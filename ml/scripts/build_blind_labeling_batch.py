"""
Generate ml/data/labeling/telegram_blind_batch.csv (Step 2.2).
Includes all 150 held-out messages from ml/data/processed/v1/telegram_test.jsonl:
  - All 58 messages that the heuristic script marked as disinformation (100% of test disinfo pool)
  - All 92 messages sampled from the benign pool in telegram_test.jsonl
Shuffled deterministically with seed=42 so script labels cannot be inferred from row order.
Columns: id, text, my_label, my_note (script label strictly excluded).
"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TG_TEST_PATH = REPO_ROOT / "ml" / "data" / "processed" / "v1" / "telegram_test.jsonl"
TG_TRAIN_PATH = REPO_ROOT / "ml" / "data" / "processed" / "v1" / "telegram_train.jsonl"
OUT_CSV_PATH = REPO_ROOT / "ml" / "data" / "labeling" / "telegram_blind_batch.csv"


def main() -> None:
    with open(TG_TEST_PATH, "r", encoding="utf-8") as f:
        test_recs = [json.loads(line) for line in f if line.strip()]
    with open(TG_TRAIN_PATH, "r", encoding="utf-8") as f:
        train_recs = [json.loads(line) for line in f if line.strip()]

    disinfo_recs = [r for r in test_recs if r.get("is_disinformation") is True]
    benign_recs = [r for r in test_recs if not r.get("is_disinformation")]

    print(f"Total telegram_test.jsonl items: {len(test_recs)}")
    print(f"  Script-marked disinformation: {len(disinfo_recs)} ({len(disinfo_recs)/len(test_recs)*100:.1f}%)")
    print(f"  Script-marked benign:         {len(benign_recs)} ({len(benign_recs)/len(test_recs)*100:.1f}%)")
    print(f"  Script category breakdown:    {dict(Counter(r['primary_label'] for r in test_recs))}")

    # Deterministic shuffle with seed 42 so order does not leak class
    rng = random.Random(42)
    batch = list(test_recs)
    rng.shuffle(batch)

    OUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["id", "text", "my_label", "my_note"])
        for rec in batch:
            clean_text = rec["text"].replace("\r\n", "\n").strip()
            writer.writerow([rec["id"], clean_text, "", ""])

    print(f"[OK] Wrote {len(batch)} blind rows to {OUT_CSV_PATH}")


if __name__ == "__main__":
    main()
