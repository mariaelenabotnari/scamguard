"""
Benchmark baseline vs balanced Telegram-augmented narrative classifier.
Compares:
  - Base TF-IDF model (trained on train.jsonl)
  - Retrained TF-IDF model (trained on train_augmented.jsonl + telegram_train.jsonl)
Evaluates across:
  - Generalization Test Set (test.jsonl)
  - Quarantined Moldovan Gold Set (gold.jsonl)
  - Real Telegram Test Set (telegram_test.jsonl)
"""

import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.pipeline import make_pipeline

ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT_DIR / "ml" / "data" / "processed" / "v1"
MODEL_SAVE_PATH = ROOT_DIR / "ml" / "models" / "narrative_classifier.joblib"
REPORTS_DIR = ROOT_DIR / "ml" / "reports"


def load_partition(split: str) -> tuple[list[str], list[int]]:
    texts, labels = [], []
    with open(PROCESSED_DIR / f"{split}.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                texts.append(d["text"])
                labels.append(d["primary_label"])
    return texts, labels


def main() -> None:
    print("=" * 70)
    print("SCAMGUARD MODEL COMPARISON & TELEGRAM EVALUATION")
    print("=" * 70)

    train_x, train_y = load_partition("train")
    train_aug_x, train_aug_y = load_partition("train_augmented")
    val_x, val_y = load_partition("val")
    test_x, test_y = load_partition("test")
    gold_x, gold_y = load_partition("gold")
    tg_test_x, tg_test_y = load_partition("telegram_test")

    print(f"Loaded partitions: train={len(train_x)}, train_augmented={len(train_aug_x)}")
    print(f"                  val={len(val_x)}, test={len(test_x)}, gold={len(gold_y)}, tg_test={len(tg_test_x)}")

    # 1. Base Model (unaugmented)
    print("\n[*] Training Baseline Model on train.jsonl...")
    m_base = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 3), max_features=25000, sublinear_tf=True),
        LogisticRegression(max_iter=1000, C=2.0, class_weight="balanced"),
    )
    m_base.fit(train_x, train_y)

    # 2. Retrained Model (balanced Telegram augmented)
    print("[*] Training Retrained Model on train_augmented.jsonl...")
    m_retrained = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 3), max_features=30000, sublinear_tf=True),
        LogisticRegression(max_iter=1000, C=2.0, class_weight="balanced"),
    )
    m_retrained.fit(train_aug_x, train_aug_y)

    # Save retrained model as production model
    MODEL_SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(m_retrained, MODEL_SAVE_PATH)
    print(f"[+] Saved retrained model to {MODEL_SAVE_PATH}")

    # Evaluate both
    splits = [
        ("Generalization Test Set (test.jsonl)", test_x, test_y),
        ("Quarantined Moldovan Gold Set (gold.jsonl)", gold_x, gold_y),
        ("Real Telegram Test Set (telegram_test.jsonl)", tg_test_x, tg_test_y),
    ]

    results = {
        "baseline_unaugmented": {},
        "retrained_balanced_augmented": {},
    }

    print("\n" + "-" * 70)
    print("EVALUATION COMPARISON: BASELINE vs RETRAINED")
    print("-" * 70)

    for split_name, xs, ys in splits:
        # Base
        base_pred = m_base.predict(xs)
        base_f1 = f1_score(ys, base_pred, average="macro", zero_division=0)
        base_acc = accuracy_score(ys, base_pred)

        # Retrained
        ret_pred = m_retrained.predict(xs)
        ret_f1 = f1_score(ys, ret_pred, average="macro", zero_division=0)
        ret_acc = accuracy_score(ys, ret_pred)

        results["baseline_unaugmented"][split_name] = {"macro_f1": round(base_f1, 4), "accuracy": round(base_acc, 4)}
        results["retrained_balanced_augmented"][split_name] = {"macro_f1": round(ret_f1, 4), "accuracy": round(ret_acc, 4)}

        delta_f1 = ret_f1 - base_f1
        print(f"\n[{split_name}]")
        print(f"  Baseline:  Macro F1 = {base_f1:.4f} | Accuracy = {base_acc*100:.1f}%")
        print(f"  Retrained: Macro F1 = {ret_f1:.4f} | Accuracy = {ret_acc*100:.1f}%")
        print(f"  Delta F1:  {'+' if delta_f1 >= 0 else ''}{delta_f1:.4f} ({(delta_f1/max(0.001, base_f1))*100:+.1f}%)")

    # Detailed Telegram Classification Report
    print("\n" + "=" * 70)
    print("REAL TELEGRAM TEST SET DETAILED CLASSIFICATION REPORT (RETRAINED)")
    print("=" * 70)
    tg_ret_pred = m_retrained.predict(tg_test_x)
    print(classification_report(tg_test_y, tg_ret_pred, zero_division=0))

    # Save benchmark report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORTS_DIR / "telegram_benchmark_comparison.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Full report saved to {report_file}")


if __name__ == "__main__":
    main()
