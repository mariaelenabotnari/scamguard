"""Trains and serializes the calibrated narrative classifier for ScamGuard.

Uses authentic training data from ml/data/processed/v1/train.jsonl.
Evaluates on test.jsonl, gold.jsonl, and hard_negatives.jsonl.
Saves the trained pipeline to ml/models/narrative_classifier.joblib.
"""

import json
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import f1_score, classification_report

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "ml" / "data" / "processed" / "v1"
EVAL_DIR = REPO_ROOT / "ml" / "eval"
MODELS_DIR = REPO_ROOT / "ml" / "models"


def load_dataset(path: Path) -> tuple[list[str], list[int]]:
    texts, labels = [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                texts.append(d["text"])
                labels.append(int(d.get("primary_label", 10)))
    return texts, labels


def train_and_evaluate() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    train_path = DATA_DIR / "train.jsonl"
    test_path = DATA_DIR / "test.jsonl"
    gold_path = DATA_DIR / "gold.jsonl"
    hard_neg_path = EVAL_DIR / "hard_negatives.jsonl"

    print(f"[*] Loading training corpus from {train_path}...")
    train_texts, train_labels = load_dataset(train_path)

    print(f"[*] Training dataset size: {len(train_texts)} samples across {len(set(train_labels))} categories.")

    pipeline = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                ngram_range=(1, 3),
                max_features=35000,
                sublinear_tf=True,
                token_pattern=r"(?u)\b\w+\b",
            ),
        ),
        (
            "clf",
            LogisticRegression(
                max_iter=600,
                class_weight="balanced",
                C=2.0,
                solver="lbfgs",
                random_state=42,
            ),
        ),
    ])

    print("[*] Fitting calibrated multilingual model...")
    pipeline.fit(train_texts, train_labels)

    # Evaluate on held-out test set
    if test_path.exists():
        test_texts, test_labels = load_dataset(test_path)
        test_preds = pipeline.predict(test_texts)
        test_f1 = f1_score(test_labels, test_preds, average="macro")
        print(f"[+] Held-Out Test Set Macro F1: {test_f1:.4f}")

    # Evaluate on Moldovan gold set
    if gold_path.exists():
        gold_texts, gold_labels = load_dataset(gold_path)
        gold_preds = pipeline.predict(gold_texts)
        gold_f1 = f1_score(gold_labels, gold_preds, average="macro")
        print(f"[+] Moldovan Gold Set Macro F1: {gold_f1:.4f}")

    # Evaluate on hard negatives
    if hard_neg_path.exists():
        neg_texts = []
        with open(hard_neg_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    neg_texts.append(json.loads(line)["text"])
        neg_preds = pipeline.predict(neg_texts)
        fps = sum(1 for p in neg_preds if p != 10)
        fpr = fps / len(neg_texts) if neg_texts else 0.0
        print(f"[+] Benign Hard Negatives FPR: {fpr * 100:.1f}% ({fps}/{len(neg_texts)})")

    # Serialize trained model
    out_model_path = MODELS_DIR / "narrative_classifier.joblib"
    joblib.dump(pipeline, out_model_path)
    print(f"[OK] Saved trained narrative classifier model to {out_model_path}")


if __name__ == "__main__":
    train_and_evaluate()

