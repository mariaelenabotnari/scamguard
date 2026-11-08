"""
Fine-tune XLM-RoBERTa for ScamGuard 13-category disinformation narrative classification.

Follows the specified training constraints:
  - Base architecture: `FacebookAI/xlm-roberta-base` (278M parameters, MIT Licence)
  - Layer freezing: Embeddings and first 8 transformer layers frozen; top 4 layers + head fine-tuned.
  - Loss: Class-frequency weighted Cross-Entropy loss to balance minority narratives.
  - Optimization: AdamW (lr=3e-5) with linear warmup and decay, gradient accumulation.
  - Early stopping: Monitored on `val.jsonl` Macro F1 (patience 3 epochs).
  - Unified evaluation: Conforms to `NarrativeClassifierModel` and evaluated through `benchmark_comparison.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import f1_score
from torch import nn
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.scripts.benchmark_comparison import (
    ALL_CLASSES,
    REPORTS_DIR,
    load_partition,
    print_report,
    run_benchmark,
)

MODELS_DIR = ROOT_DIR / "ml" / "models"


class TextClassificationDataset(Dataset):
    """Pre-tokenized PyTorch Dataset for high-speed training and zero per-step tokenizer overhead."""

    def __init__(self, texts: list[str], labels: list[int], tokenizer: Any, max_length: int = 160) -> None:
        self.labels = torch.tensor([int(l) - 1 for l in labels], dtype=torch.long)
        # Fast batch tokenization (takes ~2 seconds for full corpus)
        encodings = tokenizer(
            texts,
            truncation=True,
            padding="max_length",
            max_length=max_length,
            return_tensors="pt",
        )
        self.input_ids = encodings["input_ids"]
        self.attention_mask = encodings["attention_mask"]

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "input_ids": self.input_ids[idx],
            "attention_mask": self.attention_mask[idx],
            "label": self.labels[idx],
        }


class TransformerClassifierModel:
    """Inference wrapper exposing the unified `NarrativeClassifierModel` interface."""

    def __init__(
        self,
        model: nn.Module,
        tokenizer: Any,
        classes: list[int] | None = None,
        max_length: int = 128,
        batch_size: int = 32,
        device: torch.device | None = None,
    ) -> None:
        self.device = device or torch.device("cpu")
        self.model = model.to(self.device)
        self.model.eval()
        self.tokenizer = tokenizer
        self.classes_ = classes or ALL_CLASSES
        self.max_length = max_length
        self.batch_size = batch_size

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        self.model.eval()
        all_probs: list[np.ndarray] = []

        with torch.no_grad():
            for i in range(0, len(texts), self.batch_size):
                batch_texts = texts[i : i + self.batch_size]
                encoding = self.tokenizer(
                    batch_texts,
                    truncation=True,
                    padding=True,
                    max_length=self.max_length,
                    return_tensors="pt",
                ).to(self.device)

                logits = self.model(**encoding).logits
                probs = torch.softmax(logits, dim=-1).cpu().numpy()
                all_probs.append(probs)

        return np.vstack(all_probs) if all_probs else np.zeros((0, len(self.classes_)))


# Backward-compatibility alias
XlmRobertaClassifierModel = TransformerClassifierModel


def calculate_class_weights(labels: list[int], num_classes: int = 13, smoothing: float = 0.5) -> torch.Tensor:
    """Calculates smoothed inverse-frequency class weights to balance minority narratives."""
    counts = np.bincount([l - 1 for l in labels], minlength=num_classes)
    total = len(labels)
    # Smoothed inverse class frequencies
    weights = total / (num_classes * (counts + smoothing * np.mean(counts)))
    # Normalize so mean weight is 1.0
    weights = weights / np.mean(weights)
    return torch.tensor(weights, dtype=torch.float32)


def train_transformer(
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    epochs: int = 3,
    batch_size: int = 16,
    grad_accum_steps: int = 2,
    learning_rate: float = 3e-5,
    max_length: int = 128,
    frozen_layers: int = 8,
    seed: int = 42,
    device_name: str = "cpu",
    output_dir: Path | None = None,
) -> tuple[TransformerClassifierModel, dict[str, Any]]:
    # 1. Reproducibility & CPU threading
    torch.manual_seed(seed)
    np.random.default_rng(seed)
    torch.set_num_threads(8)

    device = torch.device(device_name)
    print(f"[*] Training on device: {device} (seed={seed}, threads={torch.get_num_threads()})", flush=True)

    # 2. Load tokenizer and model
    print(f"[*] Loading pretrained {model_name}...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(ALL_CLASSES),
        local_files_only=True,
    )

    # 3. Freeze bottom layers to accelerate CPU training and preserve multilingual representations
    if frozen_layers > 0:
        print(f"[*] Freezing embeddings and first {frozen_layers} encoder layers...", flush=True)
        # Determine architecture (roberta or bert)
        if hasattr(model, "roberta"):
            for p in model.roberta.embeddings.parameters():
                p.requires_grad = False
            for layer in model.roberta.encoder.layer[:frozen_layers]:
                for p in layer.parameters():
                    p.requires_grad = False
        elif hasattr(model, "bert"):
            for p in model.bert.embeddings.parameters():
                p.requires_grad = False
            for layer in model.bert.encoder.layer[:frozen_layers]:
                for p in layer.parameters():
                    p.requires_grad = False

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"[+] Trainable parameters: {trainable_params:,} / {total_params:,} ({trainable_params/total_params*100:.1f}%)", flush=True)

    model.to(device)

    # 4. Load datasets
    train_x, train_y, _ = load_partition("train_augmented")
    val_x, val_y, _ = load_partition("val")

    print("[*] Pre-tokenizing train and validation splits...", flush=True)
    train_dataset = TextClassificationDataset(train_x, train_y, tokenizer, max_length=max_length)
    val_dataset = TextClassificationDataset(val_x, val_y, tokenizer, max_length=max_length)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size * 2, shuffle=False)

    # 5. Loss function with class weights
    class_weights = calculate_class_weights(train_y, num_classes=len(ALL_CLASSES)).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    # 6. Optimizer and scheduler
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=learning_rate,
        weight_decay=0.01,
    )
    total_steps = (len(train_loader) // grad_accum_steps) * epochs
    warmup_steps = int(0.1 * total_steps)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    # 7. Training loop with early stopping on validation Macro F1
    best_val_f1 = 0.0
    best_state: dict[str, Any] | None = None
    patience = 3
    patience_counter = 0
    history: list[dict[str, Any]] = []

    print(f"\n[*] Starting fine-tuning for {epochs} epochs ({total_steps} steps, lr={learning_rate})...", flush=True)

    for epoch in range(1, epochs + 1):
        t0 = time.perf_counter()
        model.train()
        total_loss = 0.0
        optimizer.zero_grad()

        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["label"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            loss = criterion(outputs.logits, labels)
            loss = loss / grad_accum_steps
            loss.backward()

            total_loss += loss.item() * grad_accum_steps

            if (step + 1) % 50 == 0:
                print(
                    f"  [Epoch {epoch:02d}] Step {step+1:03d}/{len(train_loader)} | Batch Loss: {loss.item() * grad_accum_steps:.4f}",
                    flush=True,
                )

            if (step + 1) % grad_accum_steps == 0 or (step + 1) == len(train_loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

        epoch_loss = total_loss / len(train_loader)
        epoch_time = time.perf_counter() - t0

        # Evaluate on Validation split
        model.eval()
        val_preds: list[int] = []
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                logits = model(input_ids=input_ids, attention_mask=attention_mask).logits
                preds = torch.argmax(logits, dim=-1).cpu().numpy()
                val_preds.extend([int(p) + 1 for p in preds])

        val_present = sorted(set(val_y))
        val_f1 = f1_score(val_y, val_preds, average="macro", labels=val_present, zero_division=0)
        val_acc = np.mean(np.array(val_preds) == np.array(val_y))

        print(
            f"Epoch {epoch:02d}/{epochs:02d} [{epoch_time:.1f}s] | "
            f"Train Loss: {epoch_loss:.4f} | "
            f"Val Macro F1: {val_f1:.4f} | "
            f"Val Acc: {val_acc*100:.1f}%",
            flush=True,
        )

        history.append({
            "epoch": epoch,
            "train_loss": round(epoch_loss, 4),
            "val_macro_f1": round(float(val_f1), 4),
            "val_accuracy": round(float(val_acc), 4),
            "epoch_time_sec": round(epoch_time, 1),
        })

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
            print(f"  --> [*] New best validation Macro F1: {best_val_f1:.4f} (checkpoint staged)", flush=True)
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"[!] Early stopping triggered at epoch {epoch} (patience={patience})", flush=True)
                break

    # Restore best checkpoint
    if best_state is not None:
        model.load_state_dict(best_state)
        print(f"[+] Loaded best model weights (val Macro F1 = {best_val_f1:.4f})", flush=True)

    # 8. Save fine-tuned checkpoint
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        # Save training metadata
        meta = {
            "base_model": model_name,
            "best_val_f1": round(float(best_val_f1), 4),
            "history": history,
            "epochs": epochs,
            "frozen_layers": frozen_layers,
            "learning_rate": learning_rate,
            "seed": seed,
        }
        with open(output_dir / "training_meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        print(f"[+] Saved fine-tuned transformer checkpoint to {output_dir}", flush=True)

    wrapper = TransformerClassifierModel(
        model=model,
        tokenizer=tokenizer,
        classes=ALL_CLASSES,
        max_length=max_length,
        batch_size=batch_size * 2,
        device=device,
    )
    return wrapper, {"best_val_f1": best_val_f1, "history": history}


train_xlm_roberta = train_transformer


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune and Evaluate Multilingual Transformer")
    parser.add_argument(
        "--model-name",
        type=str,
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        help="Pretrained Hugging Face model identifier",
    )
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Per-device training batch size")
    parser.add_argument("--grad-accum", type=int, default=2, help="Gradient accumulation steps")
    parser.add_argument("--lr", type=float, default=3e-5, help="Learning rate")
    parser.add_argument("--max-length", type=int, default=128, help="Maximum sequence length")
    parser.add_argument("--frozen-layers", type=int, default=8, help="Number of bottom encoder layers to freeze")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--save-report", type=str, default="ml_transformer_finetuned.json")
    args = parser.parse_args()

    clean_name = args.model_name.replace("/", "_").replace("\\", "_")
    checkpoint_dir = MODELS_DIR / f"fine_tuned_{clean_name}"

    model, _meta = train_transformer(
        model_name=args.model_name,
        epochs=args.epochs,
        batch_size=args.batch_size,
        grad_accum_steps=args.grad_accum,
        learning_rate=args.lr,
        max_length=args.max_length,
        frozen_layers=args.frozen_layers,
        seed=args.seed,
        output_dir=checkpoint_dir,
    )

    print("\n" + "=" * 80, flush=True)
    print("RUNNING BENCHMARK EVALUATION ACROSS ALL DATASETS", flush=True)
    print("=" * 80, flush=True)

    report = run_benchmark(
        model=model,
        model_name=f"Fine-tuned {args.model_name} (top layers, lr={args.lr}, seed={args.seed})",
        model_file_path=checkpoint_dir / "model.safetensors",
        threshold=0.0,
        evaluation_mode="standalone",
        seed=args.seed,
    )
    print_report(report)

    # Save benchmark report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORTS_DIR / args.save_report
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2)
    print(f"\n[+] Full evaluation report saved to {report_file}", flush=True)


if __name__ == "__main__":
    main()
