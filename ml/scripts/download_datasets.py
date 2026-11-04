"""Downloads or prepares Hugging Face and curated Moldovan fact-check datasets for offline training."""

import json
from pathlib import Path

CURATED_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "seed" / "moldova_debunk_claims.jsonl"
    if (Path(__file__).resolve().parents[1] / "data" / "seed" / "moldova_debunk_claims.jsonl").exists()
    else Path(__file__).resolve().parents[1] / "data" / "curated" / "moldova_debunk_claims.jsonl"
)
PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"


def prepare_training_corpus(
    max_samples_per_category: int = 100,
) -> dict[str, int]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    samples: list[dict[str, object]] = []

    # 1. Load curated bilingual Moldovan Telegram debunk claims
    if CURATED_PATH.exists():
        with open(CURATED_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    samples.append(json.loads(line))

    # 2. Try loading Hugging Face datasets if available
    try:
        from datasets import load_dataset  # type: ignore[import-untyped]

        print("Fetching samples from Hugging Face 'moroco'...")
        moroco = load_dataset("moroco", split="train[:50]", trust_remote_code=False)
        for idx, row in enumerate(moroco):
            samples.append(
                {
                    "id": f"moroco-{idx}",
                    "text": str(row["sample"]),
                    "language": "ro",
                    "category_id": 10,
                    "category_name": "Other / not disinformation",
                    "is_disinformation": False,
                    "source": "HuggingFace moroco",
                    "debunk_url": "",
                }
            )
    except Exception as exc:  # noqa: BLE001
        print(f"Hugging Face online fetch skipped ({exc}); using curated baseline data.")

    # 3. Stratified split (70% train, 15% val, 15% test)
    train_data: list[dict[str, object]] = []
    val_data: list[dict[str, object]] = []
    test_data: list[dict[str, object]] = []

    grouped: dict[int, list[dict[str, object]]] = {}
    for s in samples:
        cat_id = int(str(s["category_id"]))
        grouped.setdefault(cat_id, []).append(s)

    for cat_id, cat_samples in grouped.items():
        n = len(cat_samples)
        n_train = max(1, int(n * 0.7))
        n_val = max(1, int(n * 0.15)) if n > 2 else 0

        train_data.extend(cat_samples[:n_train])
        if n_val > 0:
            val_data.extend(cat_samples[n_train : n_train + n_val])
            test_data.extend(cat_samples[n_train + n_val :])
        else:
            test_data.extend(cat_samples[n_train:])

    with open(PROCESSED_DIR / "train.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(item, ensure_ascii=False) + "\n" for item in train_data)

    with open(PROCESSED_DIR / "val.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(item, ensure_ascii=False) + "\n" for item in val_data)

    with open(PROCESSED_DIR / "test.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(item, ensure_ascii=False) + "\n" for item in test_data)

    summary = {
        "total_samples": len(samples),
        "train_samples": len(train_data),
        "val_samples": len(val_data),
        "test_samples": len(test_data),
        "categories_covered": len(grouped),
    }
    print(f"Dataset preparation complete: {summary}")
    return summary


if __name__ == "__main__":
    prepare_training_corpus()
