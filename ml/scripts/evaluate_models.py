"""Evaluation harness comparing TF-IDF baseline, frozen embeddings, and hybrid prototype matcher."""

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class ClassMetrics:
    category: str
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class EvaluationReport:
    model_name: str
    split_name: str
    macro_f1: float
    per_class: list[ClassMetrics]


def compute_macro_f1(
    gold_labels: list[str], predicted_labels: list[str]
) -> tuple[float, list[ClassMetrics]]:
    """Computes macro-F1 and per-class precision/recall across all observed categories."""
    categories = sorted(set(gold_labels) | set(predicted_labels))
    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)

    for gold, pred in zip(gold_labels, predicted_labels, strict=True):
        if gold == pred:
            tp[gold] += 1
        else:
            fp[pred] += 1
            fn[gold] += 1

    per_class: list[ClassMetrics] = []
    for cat in categories:
        c_tp = tp[cat]
        c_fp = fp[cat]
        c_fn = fn[cat]
        precision = c_tp / (c_tp + c_fp) if (c_tp + c_fp) > 0 else 0.0
        recall = c_tp / (c_tp + c_fn) if (c_tp + c_fn) > 0 else 0.0
        f1 = (
            (2 * precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        per_class.append(
            ClassMetrics(
                category=cat,
                precision=round(precision, 4),
                recall=round(recall, 4),
                f1=round(f1, 4),
            )
        )

    macro_f1 = (
        round(sum(m.f1 for m in per_class) / len(per_class), 4)
        if per_class
        else 0.0
    )
    return macro_f1, per_class
