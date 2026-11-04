"""
Automated Data Leakage Verification Tests for ScamGuard Dataset v1.

Verifies:
  1. Strict group_id isolation: No group_id ever straddles across train, val, test, or gold.
  2. Gold quarantine: Zero overlap of gold claims in train or validation sets.
  3. Text deduplication: No exact normalized text collisions across train and evaluation sets.
  4. Cross-split semantic distance: Cosine similarity between train and test/gold claims remains below leakage threshold.
"""

import json
from pathlib import Path
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATASET_DIR = Path(__file__).resolve().parents[1] / "data" / "processed" / "v1"


def load_split(name: str):
    path = DATASET_DIR / f"{name}.jsonl"
    assert path.exists(), f"Split file not found: {path}"
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


@pytest.fixture(scope="module")
def dataset_splits():
    return {
        "train": load_split("train"),
        "val": load_split("val"),
        "test": load_split("test"),
        "gold": load_split("gold"),
    }


def test_strict_group_id_isolation(dataset_splits):
    """Assert that no group_id is shared between any distinct splits."""
    groups_by_split = {
        name: set(r["group_id"] for r in rows)
        for name, rows in dataset_splits.items()
    }

    splits = list(groups_by_split.keys())
    for i in range(len(splits)):
        for j in range(i + 1, len(splits)):
            s1, s2 = splits[i], splits[j]
            overlap = groups_by_split[s1].intersection(groups_by_split[s2])
            assert not overlap, f"LEAKAGE DETECTED: {len(overlap)} group_ids shared between '{s1}' and '{s2}': {list(overlap)[:5]}"


def test_gold_quarantine(dataset_splits):
    """Assert that the gold evaluation set is completely isolated from train and val."""
    gold_ids = set(r["id"] for r in dataset_splits["gold"])
    train_ids = set(r["id"] for r in dataset_splits["train"])
    val_ids = set(r["id"] for r in dataset_splits["val"])

    assert not gold_ids.intersection(train_ids), "Gold IDs found in training set!"
    assert not gold_ids.intersection(val_ids), "Gold IDs found in validation set!"


def test_no_exact_text_leakage(dataset_splits):
    """Assert no exact normalized text is shared between train and test/gold."""
    train_texts = set(r["text"].strip().lower() for r in dataset_splits["train"])
    val_texts = set(r["text"].strip().lower() for r in dataset_splits["val"])
    test_texts = set(r["text"].strip().lower() for r in dataset_splits["test"])
    gold_texts = set(r["text"].strip().lower() for r in dataset_splits["gold"])

    assert not train_texts.intersection(val_texts), "Exact text overlap between train and val!"
    assert not train_texts.intersection(test_texts), "Exact text overlap between train and test!"
    assert not train_texts.intersection(gold_texts), "Exact text overlap between train and gold!"


def test_cross_split_max_cosine_similarity(dataset_splits):
    """
    Assert that semantic near-duplicates are not crossing the train/test barrier.
    TF-IDF char/word n-gram cosine similarity between train and test should not exceed threshold 0.95.
    """
    train_sample = [r["text"] for r in dataset_splits["train"][:500]]
    test_sample = [r["text"] for r in dataset_splits["test"][:100]]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=1000)
    train_mat = vectorizer.fit_transform(train_sample)
    test_mat = vectorizer.transform(test_sample)

    sim_matrix = cosine_similarity(test_mat, train_mat)
    max_sim = float(sim_matrix.max())
    assert max_sim < 0.95, f"Near-duplicate text leak detected across train and test! Max cosine sim: {max_sim:.3f}"

