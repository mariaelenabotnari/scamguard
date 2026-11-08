"""
ScamGuard Model Benchmark & Unified Comparison Harness.

Supports evaluating any model that conforms to the `NarrativeClassifierModel`
protocol (providing `predict_proba(texts: list[str]) -> np.ndarray`).

Evaluates across:
  - Generalization Test Set (test.jsonl)
  - Quarantined Moldovan Gold Set (gold.jsonl)
  - Real Telegram Test Set (telegram_test.jsonl)
  - Benign Hard Negatives (hard_negatives.jsonl)

Calculates:
  - Macro F1 (all 13 categories and present categories) with 95% percentile bootstrap CIs
  - Per-class precision, recall, F1, and support count
  - Full 13x13 Confusion Matrix
  - Overall Accuracy alongside the Majority-Class Baseline
  - Unknown rate (predictions falling below confidence threshold)
  - False Positive Rate on neutral news (120 items)
  - CPU inference throughput (texts/sec) and model disk size
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.pipeline import Pipeline, make_pipeline

ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT_DIR / "ml" / "data" / "processed" / "v1"
EVAL_DIR = ROOT_DIR / "ml" / "eval"
MODEL_SAVE_PATH = ROOT_DIR / "ml" / "models" / "narrative_classifier.joblib"
REPORTS_DIR = ROOT_DIR / "ml" / "reports"

TAXONOMY_NAMES: dict[int, str] = {
    1: "War in Ukraine & Russia justification",
    2: "Anti-EU / Europe falling apart",
    3: "Anti-NATO / anti-West",
    4: "Moldova govt & elections delegitimation",
    5: "Russophobia, language & identity",
    6: "Sanctions, energy & economy fear",
    7: "Transnistria / Gagauzia separatism",
    8: "Health, vaccines & conspiracy",
    9: "Traditional values & anti-LGBT",
    10: "Other / not disinformation (Benign)",
    11: "Financial panic & bank runs",
    12: "Forced mobilization & border militarization",
    13: "Other disinformation",
}

ALL_CLASSES = list(range(1, 14))


@runtime_checkable
class NarrativeClassifierModel(Protocol):
    """Common interface that every narrative classification candidate must implement."""

    classes_: list[int]

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        """Returns probability distribution over classes for each input text.

        Returns:
            np.ndarray of shape (len(texts), len(self.classes_))
        """
        ...


class SklearnPipelineModel:
    """Adapter wrapping an scikit-learn pipeline (e.g. TF-IDF + LogisticRegression)."""

    def __init__(self, pipeline: Pipeline, classes: list[int] | None = None) -> None:
        self.pipeline = pipeline
        raw_classes = getattr(pipeline, "classes_", None)
        if raw_classes is None and hasattr(pipeline, "named_steps"):
            classifier_step = list(pipeline.named_steps.values())[-1]
            raw_classes = getattr(classifier_step, "classes_", None)

        if raw_classes is not None:
            self.classes_ = [int(c) for c in raw_classes]
        else:
            self.classes_ = classes or list(range(1, 14))

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self.pipeline.predict_proba(texts), dtype=np.float64)


def load_partition(split: str) -> tuple[list[str], list[int], list[str]]:
    """Loads a partition from ml/data/processed/v1/{split}.jsonl."""
    texts, labels, ids = [], [], []
    path = PROCESSED_DIR / f"{split}.jsonl"
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                texts.append(d["text"])
                labels.append(d["primary_label"])
                ids.append(d.get("id", ""))
    return texts, labels, ids


def load_hard_negatives() -> tuple[list[str], list[int], list[str]]:
    """Loads the 120 benign neutral news articles from ml/eval/hard_negatives.jsonl."""
    path = EVAL_DIR / "hard_negatives.jsonl"
    texts, labels, ids = [], [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                texts.append(d["text"])
                labels.append(d.get("primary_label", 10))
                ids.append(d.get("id", ""))
    return texts, labels, ids


def bootstrap_metric_ci(
    y_true: list[int] | np.ndarray,
    y_pred: list[int] | np.ndarray,
    metric_fn: Any,
    n_bootstraps: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Computes percentile bootstrap confidence intervals."""
    rng = np.random.default_rng(seed)
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)
    n = len(y_true_arr)
    if n == 0:
        return 0.0, 0.0

    scores = []
    for _ in range(n_bootstraps):
        idx = rng.integers(0, n, n)
        val = metric_fn(y_true_arr[idx], y_pred_arr[idx])
        scores.append(val)

    scores.sort()
    low_idx = int((1.0 - ci) / 2.0 * n_bootstraps)
    high_idx = int((1.0 + ci) / 2.0 * n_bootstraps) - 1
    return float(np.round(scores[low_idx], 4)), float(
        np.round(scores[min(high_idx, len(scores) - 1)], 4)
    )


@dataclass
class ClassMetrics:
    class_id: int
    class_name: str
    precision: float
    recall: float
    f1: float
    support: int


@dataclass
class SplitEvaluationResult:
    split_name: str
    num_samples: int
    majority_class_id: int
    majority_class_name: str
    majority_baseline_accuracy: float
    accuracy: float
    unknown_rate: float
    macro_f1_all_13: float
    macro_f1_all_13_ci: tuple[float, float]
    macro_f1_present_classes: float
    macro_f1_present_classes_ci: tuple[float, float]
    present_classes: list[int]
    per_class_metrics: list[ClassMetrics]
    confusion_matrix: list[list[int]]


@dataclass
class ModelEvaluationReport:
    model_name: str
    evaluation_mode: str
    threshold: float
    eval_timestamp: str
    speed_texts_per_sec: float
    model_size_bytes: int
    model_size_mb: float
    hard_negatives_fpr: float
    hard_negatives_fpr_ci: tuple[float, float]
    splits: dict[str, SplitEvaluationResult]


def evaluate_model_on_split(
    model: NarrativeClassifierModel,
    split_name: str,
    texts: list[str],
    y_true: list[int],
    threshold: float = 0.0,
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> SplitEvaluationResult:
    probs = model.predict_proba(texts)
    max_probs = np.max(probs, axis=1)
    raw_preds = np.asarray(model.classes_)[np.argmax(probs, axis=1)]

    # Thresholding: predictions below threshold become unknown (0)
    if threshold > 0.0:
        preds = np.where(max_probs >= threshold, raw_preds, 0)
    else:
        preds = raw_preds

    unknown_count = int(np.sum(preds == 0))
    unknown_rate = float(np.round(unknown_count / len(texts), 4))
    accuracy = float(np.round(np.mean(preds == y_true), 4))

    # Majority baseline
    counts = Counter(y_true)
    maj_cat, maj_count = counts.most_common(1)[0]
    maj_baseline = float(np.round(maj_count / len(y_true), 4))

    # Present classes in this ground truth split
    present_classes = sorted(counts.keys())

    # 1. Macro F1 across all 13 taxonomy classes
    macro_f1_all = float(
        np.round(
            f1_score(y_true, preds, average="macro", labels=ALL_CLASSES, zero_division=0),
            4,
        )
    )

    def calc_macro_f1_all(yt: np.ndarray, yp: np.ndarray) -> float:
        return float(
            f1_score(yt, yp, average="macro", labels=ALL_CLASSES, zero_division=0)
        )

    f1_all_ci = bootstrap_metric_ci(
        y_true, preds, calc_macro_f1_all, n_bootstraps=n_bootstraps, seed=seed
    )

    # 2. Macro F1 across classes present in this split
    macro_f1_pres = float(
        np.round(
            f1_score(
                y_true, preds, average="macro", labels=present_classes, zero_division=0
            ),
            4,
        )
    )

    def calc_macro_f1_pres(yt: np.ndarray, yp: np.ndarray) -> float:
        return float(
            f1_score(yt, yp, average="macro", labels=present_classes, zero_division=0)
        )

    f1_pres_ci = bootstrap_metric_ci(
        y_true, preds, calc_macro_f1_pres, n_bootstraps=n_bootstraps, seed=seed
    )

    # Per-class metrics
    p, r, f, s = precision_recall_fscore_support(
        y_true, preds, labels=ALL_CLASSES, zero_division=0
    )
    per_class = []
    for cid, prec, rec, f_val, sup in zip(ALL_CLASSES, p, r, f, s, strict=False):
        per_class.append(
            ClassMetrics(
                class_id=int(cid),
                class_name=TAXONOMY_NAMES.get(int(cid), f"Category {cid}"),
                precision=float(np.round(prec, 4)),
                recall=float(np.round(rec, 4)),
                f1=float(np.round(f_val, 4)),
                support=int(sup),
            )
        )

    # Confusion Matrix (13x13 over classes 1..13)
    cm = confusion_matrix(y_true, preds, labels=ALL_CLASSES).tolist()

    return SplitEvaluationResult(
        split_name=split_name,
        num_samples=len(texts),
        majority_class_id=int(maj_cat),
        majority_class_name=TAXONOMY_NAMES.get(int(maj_cat), f"Category {maj_cat}"),
        majority_baseline_accuracy=maj_baseline,
        accuracy=accuracy,
        unknown_rate=unknown_rate,
        macro_f1_all_13=macro_f1_all,
        macro_f1_all_13_ci=f1_all_ci,
        macro_f1_present_classes=macro_f1_pres,
        macro_f1_present_classes_ci=f1_pres_ci,
        present_classes=present_classes,
        per_class_metrics=per_class,
        confusion_matrix=cm,
    )


def evaluate_hard_negatives(
    model: NarrativeClassifierModel,
    threshold: float = 0.0,
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> tuple[float, tuple[float, float]]:
    texts, labels, _ = load_hard_negatives()
    probs = model.predict_proba(texts)
    max_probs = np.max(probs, axis=1)
    raw_preds = np.asarray(model.classes_)[np.argmax(probs, axis=1)]

    if threshold > 0.0:
        preds = np.where(max_probs >= threshold, raw_preds, 0)
    else:
        preds = raw_preds

    # Disinformation = any category other than 10 (Benign) and 0 (Unknown)
    is_disinfo = (preds != 10) & (preds != 0)
    fpr = float(np.round(np.mean(is_disinfo), 4))

    def calc_fpr(yt: np.ndarray, yp: np.ndarray) -> float:
        return float(np.mean((yp != 10) & (yp != 0)))

    fpr_ci = bootstrap_metric_ci(
        labels, preds, calc_fpr, n_bootstraps=n_bootstraps, seed=seed
    )
    return fpr, fpr_ci


def benchmark_speed(
    model: NarrativeClassifierModel, texts: list[str], n_runs: int = 3
) -> float:
    """Measures texts processed per second on CPU."""
    # Warmup
    _ = model.predict_proba(texts[: min(30, len(texts))])

    timings = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        _ = model.predict_proba(texts)
        t1 = time.perf_counter()
        timings.append(t1 - t0)

    avg_time = float(np.mean(timings))
    return float(np.round(len(texts) / max(0.0001, avg_time), 1))


def run_benchmark(
    model: NarrativeClassifierModel,
    model_name: str,
    model_file_path: Path | None = None,
    threshold: float = 0.0,
    evaluation_mode: str = "standalone",
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> ModelEvaluationReport:
    """Runs the full evaluation benchmark across all target partitions."""
    # Model size
    if model_file_path and model_file_path.exists():
        size_bytes = os.path.getsize(model_file_path)
    else:
        size_bytes = 0
    size_mb = float(np.round(size_bytes / (1024 * 1024), 2))

    # Partitions
    test_x, test_y, _ = load_partition("test")
    gold_x, gold_y, _ = load_partition("gold")
    tg_x, tg_y, _ = load_partition("telegram_test")

    speed = benchmark_speed(model, test_x)
    hn_fpr, hn_fpr_ci = evaluate_hard_negatives(
        model, threshold=threshold, n_bootstraps=n_bootstraps, seed=seed
    )

    splits = {
        "test": evaluate_model_on_split(
            model,
            "Generalization Test Set (test.jsonl)",
            test_x,
            test_y,
            threshold=threshold,
            n_bootstraps=n_bootstraps,
            seed=seed,
        ),
        "gold": evaluate_model_on_split(
            model,
            "Quarantined Moldovan Gold Set (gold.jsonl)",
            gold_x,
            gold_y,
            threshold=threshold,
            n_bootstraps=n_bootstraps,
            seed=seed,
        ),
        "telegram_test": evaluate_model_on_split(
            model,
            "Real Telegram Test Set (telegram_test.jsonl)",
            tg_x,
            tg_y,
            threshold=threshold,
            n_bootstraps=n_bootstraps,
            seed=seed,
        ),
    }

    return ModelEvaluationReport(
        model_name=model_name,
        evaluation_mode=evaluation_mode,
        threshold=threshold,
        eval_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        speed_texts_per_sec=speed,
        model_size_bytes=size_bytes,
        model_size_mb=size_mb,
        hard_negatives_fpr=hn_fpr,
        hard_negatives_fpr_ci=hn_fpr_ci,
        splits=splits,
    )


def print_report(report: ModelEvaluationReport) -> None:
    print("=" * 80)
    print(f"SCAMGUARD BENCHMARK REPORT: {report.model_name}")
    print(f"Mode: {report.evaluation_mode} | Threshold: {report.threshold} | Speed: {report.speed_texts_per_sec} texts/s | Size: {report.model_size_mb} MB")
    print(f"Benign Hard Negatives FPR: {report.hard_negatives_fpr*100:.1f}% [95% CI: {report.hard_negatives_fpr_ci[0]*100:.1f}%, {report.hard_negatives_fpr_ci[1]*100:.1f}%]")
    print("=" * 80)

    for split_key, s in report.splits.items():
        print(f"\n--- [{split_key.upper()}] {s.split_name} (N={s.num_samples}) ---")
        print(f"  Macro F1 (all 13 categories):     {s.macro_f1_all_13:.4f} [95% CI: {s.macro_f1_all_13_ci[0]:.4f}, {s.macro_f1_all_13_ci[1]:.4f}]")
        print(f"  Macro F1 (present {len(s.present_classes)} categories):  {s.macro_f1_present_classes:.4f} [95% CI: {s.macro_f1_present_classes_ci[0]:.4f}, {s.macro_f1_present_classes_ci[1]:.4f}]")
        print(f"  Accuracy:                         {s.accuracy*100:.1f}%")
        print(f"  Majority Baseline:                {s.majority_baseline_accuracy*100:.1f}% ({s.majority_class_name})")
        print(f"  Unknown Rate:                     {s.unknown_rate*100:.1f}%")

        print("\n  Per-Class Performance:")
        print(f"  {'ID':<3} | {'Category Name':<42} | {'Prec':<6} | {'Recall':<6} | {'F1':<6} | {'Support'}")
        print("  " + "-" * 75)
        for c in s.per_class_metrics:
            if c.support > 0 or c.f1 > 0:
                print(f"  {c.class_id:<3} | {c.class_name[:42]:<42} | {c.precision:.4f} | {c.recall:.4f} | {c.f1:.4f} | {c.support}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ScamGuard Narrative Benchmark")
    parser.add_argument("--retrain", action="store_true", help="Retrain TF-IDF baseline model before evaluating")
    parser.add_argument("--threshold", type=float, default=0.0, help="Confidence threshold below which prediction is marked unknown")
    parser.add_argument("--save-report", type=str, default="ml_transformer_baseline.json", help="Report filename in ml/reports/")
    args = parser.parse_args()

    if args.retrain or not MODEL_SAVE_PATH.exists():
        print("[*] Training balanced TF-IDF + LogisticRegression model on train_augmented.jsonl...")
        train_aug_x, train_aug_y, _ = load_partition("train_augmented")
        pipeline = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 3), max_features=30000, sublinear_tf=True),
            LogisticRegression(max_iter=1000, C=2.0, class_weight="balanced"),
        )
        pipeline.fit(train_aug_x, train_aug_y)
        MODEL_SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, MODEL_SAVE_PATH)
        print(f"[+] Saved model to {MODEL_SAVE_PATH}")
    else:
        print(f"[*] Loading existing baseline model from {MODEL_SAVE_PATH}...")
        pipeline = joblib.load(MODEL_SAVE_PATH)

    model = SklearnPipelineModel(pipeline)
    report = run_benchmark(
        model=model,
        model_name="Baseline TF-IDF + Logistic Regression",
        model_file_path=MODEL_SAVE_PATH,
        threshold=args.threshold,
        evaluation_mode="standalone",
    )
    print_report(report)

    # Save JSON report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = REPORTS_DIR / args.save_report
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2)
    print(f"\n[+] Saved full evaluation report to {out_file}")


if __name__ == "__main__":
    main()
