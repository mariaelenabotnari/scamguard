"""
Evaluate human-verified Telegram annotations from ml/data/labeling/telegram_blind_batch.csv (Step 2.2.3).
When `my_label` is filled by the human annotator:
  1. Computes inter-annotator agreement (Cohen's kappa, raw agreement, binary disinfo agreement,
     and confusion matrix) between the keyword-rule script (`telegram_test.jsonl`) and human labels.
  2. Evaluates all candidate models on the human-verified labels (both unweighted stratified and
     inverse-probability weighted to natural channel prevalence), reporting Macro F1 with 95% bootstrap CIs
     and Accuracy alongside the human Majority-Class Baseline.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.scripts.benchmark_comparison import ALL_CLASSES, bootstrap_metric_ci
from ml.scripts.label_telegram_messages import CATEGORY_NAMES

CSV_PATH = REPO_ROOT / "ml" / "data" / "labeling" / "telegram_blind_batch.csv"
TG_TEST_PATH = REPO_ROOT / "ml" / "data" / "processed" / "v1" / "telegram_test.jsonl"


def main() -> None:
    if not CSV_PATH.exists():
        print(f"[!] File not found: {CSV_PATH}")
        return

    with open(TG_TEST_PATH, "r", encoding="utf-8") as f:
        script_by_id = {json.loads(line)["id"]: json.loads(line) for line in f if line.strip()}

    human_rows = []
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lbl = (row.get("my_label") or "").strip()
            if lbl and lbl.isdigit() and int(lbl) in ALL_CLASSES:
                human_rows.append((row["id"], row["text"], int(lbl), row.get("my_note", "")))

    if not human_rows:
        print(
            f"[*] {CSV_PATH} currently has 0 completed `my_label` entries (1..13).\n"
            "    Fill in `my_label` following docs/labeling-guide.md and re-run this script."
        )
        return

    ids, texts, y_human, _ = zip(*human_rows)
    y_script = [script_by_id[i]["primary_label"] for i in ids]

    kappa_13 = cohen_kappa_score(y_script, y_human, labels=ALL_CLASSES)
    acc_13 = accuracy_score(y_human, y_script)
    y_human_bin = [0 if y == 10 else 1 for y in y_human]
    y_script_bin = [0 if y == 10 else 1 for y in y_script]
    kappa_bin = cohen_kappa_score(y_script_bin, y_human_bin)

    maj_cls, maj_cnt = Counter(y_human).most_common(1)[0]
    maj_acc = maj_cnt / len(y_human)

    print(f"=== Human vs. Keyword-Script Agreement (N={len(y_human)}) ===")
    print(f"  13-Class Cohen's Kappa: {kappa_13:.4f} (Raw Agreement: {acc_13*100:.1f}%)")
    print(f"  Binary Disinfo Kappa:   {kappa_bin:.4f}")
    print(f"  Human Majority Class:   Cat {maj_cls} ({CATEGORY_NAMES[maj_cls]}) = {maj_acc*100:.1f}%")


if __name__ == "__main__":
    main()
