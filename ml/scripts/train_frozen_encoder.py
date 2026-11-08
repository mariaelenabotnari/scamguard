"""
Train and evaluate Candidate 1: Frozen Multilingual Encoder + Logistic Regression.

Architecture:
  - Frozen dense multilingual encoder: `intfloat/multilingual-e5-base` (or `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`)
  - Linear classification head: `LogisticRegression(C=2.0, class_weight="balanced", max_iter=1000)`
  - Evaluated via the unified `NarrativeClassifierModel` interface through `benchmark_comparison.py`.

Rules followed:
  - Zero leakage: trained on train_augmented.jsonl, tuned on val.jsonl, evaluated on test.jsonl, gold.jsonl, telegram_test.jsonl
  - Fixed random seeds (default 42, supports multiple seeds)
  - 95% bootstrap confidence intervals and majority baseline reported for every metric.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression

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

CACHE_DIR = ROOT_DIR / "ml" / "data" / "cache"
MODELS_DIR = ROOT_DIR / "ml" / "models"


class FrozenEncoderClassifier:
    """Wrapper coupling a frozen sentence encoder with a trained logistic regression head."""

    def __init__(
        self,
        encoder_name: str,
        classifier: LogisticRegression,
        classes: list[int] | None = None,
        prefix: str = "passage: ",
        batch_size: int = 64,
    ) -> None:
        self.encoder_name = encoder_name
        self.classifier = classifier
        self.prefix = prefix
        self.batch_size = batch_size
        self.classes_ = classes or [int(c) for c in classifier.classes_]
        self._encoder: SentenceTransformer | None = None

    def _get_encoder(self) -> SentenceTransformer:
        if self._encoder is None:
            self._encoder = SentenceTransformer(self.encoder_name, local_files_only=True)
        return self._encoder

    def encode(self, texts: list[str]) -> np.ndarray:
        enc = self._get_encoder()
        prefixed = [f"{self.prefix}{t}" for t in texts] if self.prefix else texts
        return np.asarray(
            enc.encode(
                prefixed,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ),
            dtype=np.float64,
        )

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        features = self.encode(texts)
        raw_probs = self.classifier.predict_proba(features)
        # Ensure output is aligned to ALL_CLASSES (1..13)
        prob_matrix = np.zeros((len(texts), len(ALL_CLASSES)), dtype=np.float64)
        for i, cls_id in enumerate(self.classifier.classes_):
            if int(cls_id) in ALL_CLASSES:
                col_idx = ALL_CLASSES.index(int(cls_id))
                prob_matrix[:, col_idx] = raw_probs[:, i]
        return prob_matrix


def get_cached_embeddings(
    encoder_name: str,
    split_name: str,
    texts: list[str],
    prefix: str = "passage: ",
    batch_size: int = 64,
) -> np.ndarray:
    """Caches dense embeddings to disk so multi-seed training runs instantly."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    clean_name = encoder_name.replace("/", "_").replace("\\", "_")
    cache_file = CACHE_DIR / f"{clean_name}_{split_name}_embeddings.npy"

    if cache_file.exists():
        print(f"[*] Loading cached embeddings from {cache_file.name}...")
        return np.load(cache_file)

    print(f"[*] Extracting embeddings for '{split_name}' ({len(texts)} texts) with {encoder_name}...")
    t0 = time.perf_counter()
    encoder = SentenceTransformer(encoder_name, local_files_only=True)
    prefixed = [f"{prefix}{t}" for t in texts] if prefix else texts
    emb = encoder.encode(
        prefixed,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    np.save(cache_file, emb)
    print(f"[+] Saved embeddings to {cache_file.name} in {time.perf_counter() - t0:.1f}s")
    return np.asarray(emb, dtype=np.float64)


def train_and_eval_frozen_encoder(
    encoder_name: str = "intfloat/multilingual-e5-base",
    prefix: str = "passage: ",
    c_param: float = 2.0,
    seed: int = 42,
    batch_size: int = 64,
    save_model_path: Path | None = None,
) -> Any:
    # 1. Load Partitions
    train_x, train_y, _ = load_partition("train_augmented")
    val_x, val_y, _ = load_partition("val")

    # 2. Extract / load dense representations
    train_emb = get_cached_embeddings(encoder_name, "train_augmented", train_x, prefix=prefix, batch_size=batch_size)
    val_emb = get_cached_embeddings(encoder_name, "val", val_x, prefix=prefix, batch_size=batch_size)

    # 3. Fit Logistic Regression Head
    print(f"\n[*] Training Logistic Regression (C={c_param}, class_weight='balanced', seed={seed})...")
    clf = LogisticRegression(
        C=c_param,
        class_weight="balanced",
        max_iter=1000,
        random_state=seed,
        solver="lbfgs",
    )
    clf.fit(train_emb, train_y)

    val_acc = np.mean(clf.predict(val_emb) == val_y)
    print(f"[+] Validation Accuracy: {val_acc*100:.1f}%")

    # 4. Wrap in common interface
    wrapper = FrozenEncoderClassifier(
        encoder_name=encoder_name,
        classifier=clf,
        classes=ALL_CLASSES,
        prefix=prefix,
        batch_size=batch_size,
    )

    # 5. Save model checkpoint
    if save_model_path:
        save_model_path.parent.mkdir(parents=True, exist_ok=True)
        # We save the classifier and metadata (the encoder stays frozen in HuggingFace cache)
        checkpoint = {
            "encoder_name": encoder_name,
            "classifier": clf,
            "classes_": ALL_CLASSES,
            "prefix": prefix,
            "c_param": c_param,
            "seed": seed,
        }
        joblib.dump(checkpoint, save_model_path)
        print(f"[+] Saved model checkpoint to {save_model_path}")

    return wrapper


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Frozen Multilingual Encoder Classifier")
    parser.add_argument(
        "--encoder",
        type=str,
        default="intfloat/multilingual-e5-base",
        choices=[
            "intfloat/multilingual-e5-base",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        ],
        help="Pretrained sentence encoder identifier",
    )
    parser.add_argument("--c", type=float, default=2.0, help="L2 regularization inverse strength")
    parser.add_argument("--prefix", type=str, default="passage: ", help="Text prefix for encoder (passage: for e5)")
    parser.add_argument("--batch-size", type=int, default=64, help="Embedding extraction batch size")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42], help="Random seeds for evaluation")
    parser.add_argument("--save-report", type=str, default="ml_transformer_frozen_encoder.json")
    args = parser.parse_args()

    # For paraphrase-multilingual-MiniLM-L12-v2, no prefix is needed
    prefix = "" if "MiniLM" in args.encoder else args.prefix

    save_path = MODELS_DIR / "frozen_multilingual_encoder.joblib"
    all_reports = []

    for seed in args.seeds:
        print("\n" + "=" * 80)
        print(f"RUNNING EXPERIMENT: {args.encoder} (seed={seed})")
        print("=" * 80)

        model = train_and_eval_frozen_encoder(
            encoder_name=args.encoder,
            prefix=prefix,
            c_param=args.c,
            seed=seed,
            batch_size=args.batch_size,
            save_model_path=save_path if seed == args.seeds[0] else None,
        )

        report = run_benchmark(
            model=model,
            model_name=f"Frozen {args.encoder} + LogisticRegression (seed={seed})",
            model_file_path=save_path,
            threshold=0.0,
            evaluation_mode="standalone",
            seed=seed,
        )
        print_report(report)
        all_reports.append(asdict(report))

    # Save benchmark report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORTS_DIR / args.save_report
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(all_reports[0] if len(all_reports) == 1 else all_reports, f, indent=2)
    print(f"\n[+] Full report saved to {report_file}")


if __name__ == "__main__":
    main()
