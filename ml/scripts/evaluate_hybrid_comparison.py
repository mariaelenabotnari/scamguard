"""
Benchmark and compare all three models inside the full ScamGuard hybrid pipeline:
  1. Baseline: TF-IDF + Logistic Regression
  2. Candidate 1: Frozen Multilingual MiniLM + Logistic Regression
  3. Candidate 2: Fine-Tuned Multilingual MiniLM Transformer

Evaluates on:
  - telegram_test.jsonl (150 authentic Telegram posts)
  - gold.jsonl (150 quarantined Moldovan claims)
  - hard_negatives.jsonl (120 benign neutral news articles)

Under the ScamGuard multi-signal assertion gate with calibrated threshold.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import DatabaseManager
from app.services.narrative_classifier_service import (
    _NARRATIVE_CATEGORIES,
    NarrativeClassifierService,
)

from ml.scripts.benchmark_comparison import (
    ALL_CLASSES,
    bootstrap_metric_ci,
    load_hard_negatives,
    load_partition,
)
from ml.scripts.train_transformer import TransformerClassifierModel

CAT_NAME_TO_ID = {rule.name: rule.cat_id for rule in _NARRATIVE_CATEGORIES}
CAT_NAME_TO_ID["Other / not disinformation"] = 10
CAT_NAME_TO_ID["Other / not disinformation (Benign)"] = 10
CAT_NAME_TO_ID["unknown"] = 10


def evaluate_service_on_split(
    service: NarrativeClassifierService,
    texts: list[str],
    labels: list[int],
    threshold: float = 0.38,
    seed: int = 42,
) -> dict[str, Any]:
    preds: list[int] = []
    t0 = time.perf_counter()

    for i, t in enumerate(texts):
        res = service.classify_one(
            target_id=f"bench-{i}",
            target_type="message",
            raw_text=t,
            confidence_threshold=threshold,
        )
        cat_id = CAT_NAME_TO_ID.get(res.category, 10)
        preds.append(cat_id)

    elapsed = time.perf_counter() - t0
    y_true = np.array(labels)
    y_pred = np.array(preds)

    acc = float(np.mean(y_true == y_pred))
    present = sorted(set(labels))
    f1_present = float(f1_score(y_true, y_pred, average="macro", labels=present, zero_division=0))
    f1_all = float(f1_score(y_true, y_pred, average="macro", labels=ALL_CLASSES, zero_division=0))

    ci_present = bootstrap_metric_ci(
        y_true,
        y_pred,
        lambda yt, yp: float(f1_score(yt, yp, average="macro", labels=present, zero_division=0)),
        seed=seed,
    )
    ci_all = bootstrap_metric_ci(
        y_true,
        y_pred,
        lambda yt, yp: float(f1_score(yt, yp, average="macro", labels=ALL_CLASSES, zero_division=0)),
        seed=seed,
    )

    return {
        "num_samples": len(texts),
        "accuracy": round(acc, 4),
        "macro_f1_present": round(f1_present, 4),
        "macro_f1_present_ci": [round(ci_present[0], 4), round(ci_present[1], 4)],
        "macro_f1_all_13": round(f1_all, 4),
        "macro_f1_all_13_ci": [round(ci_all[0], 4), round(ci_all[1], 4)],
        "speed_texts_per_sec": round(len(texts) / max(elapsed, 0.001), 1),
    }


def evaluate_hard_negatives(service: NarrativeClassifierService, texts: list[str], threshold: float = 0.38) -> float:
    fp_count = 0
    for i, t in enumerate(texts):
        res = service.classify_one(
            target_id=f"hn-{i}",
            target_type="message",
            raw_text=t,
            confidence_threshold=threshold,
        )
        if res.is_disinformation:
            fp_count += 1
    return round(fp_count / len(texts), 4)


def main() -> None:
    print("=" * 80)
    print("SCAMGUARD HYBRID PIPELINE BENCHMARK (Multi-Signal Gating & Threshold Calibration)")
    print("=" * 80)

    # 1. Load data
    tg_x, tg_y, _ = load_partition("telegram_test")
    gold_x, gold_y, _ = load_partition("gold")
    hn_x, _, _ = load_hard_negatives()

    db_manager = DatabaseManager(":memory:")
    service = NarrativeClassifierService(db_manager=db_manager)

    # Paths
    baseline_path = ROOT_DIR / "ml" / "models" / "narrative_classifier.joblib"
    frozen_path = ROOT_DIR / "ml" / "models" / "frozen_multilingual_encoder.joblib"
    finetuned_dir = ROOT_DIR / "ml" / "models" / "fine_tuned_sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2"

    models_to_test: list[tuple[str, Any]] = []

    # Model 1: Baseline
    if baseline_path.exists():
        models_to_test.append(("TF-IDF + LogisticRegression (Baseline)", joblib.load(baseline_path)))

    # Model 2: Frozen MiniLM + LogisticRegression
    if frozen_path.exists():
        models_to_test.append(("Frozen MiniLM + LogisticRegression (Candidate 1)", joblib.load(frozen_path)))

    # Model 3: Fine-Tuned MiniLM
    if finetuned_dir.exists():
        print(f"[*] Loading fine-tuned checkpoint from {finetuned_dir.name}...")
        tok = AutoTokenizer.from_pretrained(finetuned_dir, local_files_only=True)
        ft_model = AutoModelForSequenceClassification.from_pretrained(finetuned_dir, local_files_only=True)
        wrapper = TransformerClassifierModel(
            model=ft_model,
            tokenizer=tok,
            classes=ALL_CLASSES,
            max_length=128,
            batch_size=32,
        )
        models_to_test.append(("Fine-Tuned MiniLM Transformer (Candidate 2)", wrapper))

    results: dict[str, Any] = {}

    for name, model_obj in models_to_test:
        print(f"\n---> Evaluating Hybrid Pipeline with: {name}", flush=True)
        service._trained_model = model_obj

        # Calibrate across thresholds [0.38, 0.50]
        for tau in [0.38, 0.50]:
            print(f"   [Threshold tau = {tau:.2f}]", flush=True)
            tg_res = evaluate_service_on_split(service, tg_x, tg_y, threshold=tau)
            gold_res = evaluate_service_on_split(service, gold_x, gold_y, threshold=tau)
            hn_fpr = evaluate_hard_negatives(service, hn_x, threshold=tau)

            print(f"     Telegram Test Macro F1: {tg_res['macro_f1_present']} {tg_res['macro_f1_present_ci']} | Acc: {tg_res['accuracy']*100:.1f}%", flush=True)
            print(f"     Gold Set Macro F1:      {gold_res['macro_f1_present']} {gold_res['macro_f1_present_ci']} | Acc: {gold_res['accuracy']*100:.1f}%", flush=True)
            print(f"     Benign Hard Neg FPR:    {hn_fpr*100:.1f}% | Speed: {tg_res['speed_texts_per_sec']} texts/s", flush=True)

            results[f"{name} (tau={tau:.2f})"] = {
                "telegram_test": tg_res,
                "gold": gold_res,
                "hard_negatives_fpr": hn_fpr,
            }

    out_file = ROOT_DIR / "ml" / "reports" / "hybrid_pipeline_comparison.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Hybrid pipeline comparison saved to {out_file}", flush=True)


if __name__ == "__main__":
    main()
