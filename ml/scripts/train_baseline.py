"""
Train and evaluate baseline narrative classifier on ScamGuard dataset v1.
Baselines:
  1. TF-IDF + Logistic Regression
  2. Evaluation across validation, test, and quarantined gold partitions.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, accuracy_score


ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT_DIR / "ml" / "data" / "processed" / "v1"


def load_partition(split_name: str) -> Tuple[List[str], List[int]]:
    path = PROCESSED_DIR / f"{split_name}.jsonl"
    texts = []
    labels = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                texts.append(rec["text"])
                labels.append(rec["primary_label"])
    return texts, labels


def main() -> None:
    print("=" * 70)
    print("SCAMGUARD ML BASELINE TRAINING & BENCHMARKING")
    print("=" * 70)

    print("\n[*] Loading dataset partitions from", PROCESSED_DIR)
    train_texts, train_y = load_partition("train")
    val_texts, val_y = load_partition("val")
    test_texts, test_y = load_partition("test")
    gold_texts, gold_y = load_partition("gold")

    print(f"Loaded: train={len(train_texts)}, val={len(val_texts)}, test={len(test_texts)}, gold={len(gold_texts)}")

    print("\n[*] Fitting TF-IDF Vectorizer (word + char ngrams)...")
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 3),
        max_features=25000,
        sublinear_tf=True,
    )
    X_train = vectorizer.fit_transform(train_texts)
    X_val = vectorizer.transform(val_texts)
    X_test = vectorizer.transform(test_texts)
    X_gold = vectorizer.transform(gold_texts)

    print("[*] Training Logistic Regression classifier (multinomial)...")
    clf = LogisticRegression(max_iter=1000, C=2.0, class_weight="balanced")
    clf.fit(X_train, train_y)

    print("\n" + "-" * 70)
    print("BENCHMARK EVALUATION RESULTS")
    print("-" * 70)

    for name, X_split, y_split in [("Validation", X_val, val_y), ("Test (Generalization)", X_test, test_y), ("Moldovan Gold Set", X_gold, gold_y)]:
        y_pred = clf.predict(X_split)
        acc = accuracy_score(y_split, y_pred)
        macro_f1 = f1_score(y_split, y_pred, average="macro", zero_division=0)
        weighted_f1 = f1_score(y_split, y_pred, average="weighted", zero_division=0)
        print(f"\n[{name}]")
        print(f"  Accuracy:    {acc:.4f} ({acc*100:.1f}%)")
        print(f"  Macro F1:    {macro_f1:.4f}")
        print(f"  Weighted F1: {weighted_f1:.4f}")

    print("\n" + "=" * 70)
    print("[SUCCESS] Baseline benchmark complete.")


if __name__ == "__main__":
    main()

