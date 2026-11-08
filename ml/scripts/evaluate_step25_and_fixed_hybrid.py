"""
Evaluate:
  1. Fixed Hybrid NarrativeClassifierService (with validation-tuned gate fix) across all splits
     and hard_negatives_v1 / hard_negatives_v2 (with Clopper-Pearson 95% CIs).
  2. Step 2.5 SimilarityService with SentenceTransformerEmbedder default (USE_DENSE_SIMILARITY_EMBEDDER=True)
     vs DeterministicMultilingualEmbedder fallback (USE_DENSE_SIMILARITY_EMBEDDER=False) on:
       - ml/eval/pairs_eval.jsonl (317 pairs: ALL, RO-RO, RU-RU, RO-RU + speed in pairs/sec)
       - ml/eval/clusters_eval.jsonl (35 cascades: B-cubed Precision, Recall, F1 + speed)
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import beta

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import DatabaseManager
from app.dtos.collector_dto import StoredMessageDto
from app.repositories.cluster_repository import SqliteClusterRepository
from app.repositories.message_repository import SqliteMessageRepository
from app.repositories.user_repository import SqliteParameterRepository
from app.services.clustering_service import ClusteringService
from app.services.narrative_classifier_service import (
    NarrativeClassifierService,
    _NARRATIVE_CATEGORIES,
)
from app.services.similarity_service import SimilarityService
from app.services.text_normaliser import TextNormaliser
from ml.eval.run import evaluate_clusters, evaluate_similarity
from ml.scripts.benchmark_comparison import ALL_CLASSES, bootstrap_metric_ci, load_partition

CAT_NAME_TO_ID = {rule.name: rule.cat_id for rule in _NARRATIVE_CATEGORIES}
CAT_NAME_TO_ID["Other / not disinformation"] = 10
CAT_NAME_TO_ID["Other / not disinformation (Benign)"] = 10
CAT_NAME_TO_ID["unknown"] = 0


def clopper_pearson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    low = 0.0 if k == 0 else float(beta.ppf(alpha / 2.0, k, n - k + 1))
    high = 1.0 if k == n else float(beta.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return (round(low, 4), round(high, 4))


def fast_macro_f1(yt: np.ndarray, yp: np.ndarray) -> float:
    total = 0.0
    for c in ALL_CLASSES:
        t_c = yt == c
        p_c = yp == c
        tp = int(np.count_nonzero(t_c & p_c))
        if tp > 0:
            total += (2.0 * tp) / (int(np.count_nonzero(t_c)) + int(np.count_nonzero(p_c)))
    return total / len(ALL_CLASSES)


def main() -> None:
    # 1. Evaluate Fixed Hybrid NarrativeClassifierService
    svc = NarrativeClassifierService(DatabaseManager(":memory:"))
    svc._ensure_loaded()

    splits = {}
    for s_name in ["val", "test", "gold", "telegram_test"]:
        texts, y, _ = load_partition(s_name)
        splits[s_name] = (texts, y)
    splits["gold_unique_30"] = (splits["gold"][0][:30], splits["gold"][1][:30])

    hybrid_results: dict[str, Any] = {"splits": {}, "hard_negatives": {}}
    for s_name, (texts, y_true) in splits.items():
        t0 = time.perf_counter()
        preds = []
        for i, t in enumerate(texts):
            res = svc.classify_one(target_id=f"{s_name}-{i}", target_type="message", raw_text=t, confidence_threshold=0.38)
            if not res.is_disinformation:
                preds.append(0 if res.category == "unknown" else 10)
            else:
                preds.append(CAT_NAME_TO_ID.get(res.category, 10))
        elapsed = max(1e-6, time.perf_counter() - t0)
        yt_arr = np.asarray(y_true, dtype=int)
        yp_arr = np.asarray(preds, dtype=int)
        mf1 = fast_macro_f1(yt_arr, yp_arr)
        ci_l, ci_h = bootstrap_metric_ci(yt_arr, yp_arr, fast_macro_f1, n_bootstraps=1000, seed=42)
        acc = float(np.mean(yt_arr == yp_arr))
        maj_c, maj_cnt = Counter(y_true).most_common(1)[0]
        unk = sum(1 for p in preds if p == 0) / len(preds)
        benign_fp = sum(1 for g, p in zip(y_true, preds) if g == 10 and p not in (0, 10))
        benign_tot = sum(1 for g in y_true if g == 10)
        hybrid_results["splits"][s_name] = {
            "n": len(y_true),
            "macro_f1": round(mf1, 4),
            "ci_95": [round(ci_l, 4), round(ci_h, 4)],
            "accuracy": round(acc, 4),
            "majority_accuracy": round(maj_cnt / len(y_true), 4),
            "unknown_rate": round(unk, 4),
            "benign_fp": f"{benign_fp}/{benign_tot}",
            "texts_per_sec": round(len(texts) / elapsed, 1),
        }

    for hn_name, hn_file in [("hard_negatives_v1", "hard_negatives.jsonl"), ("hard_negatives_v2", "hard_negatives_v2.jsonl")]:
        with open(REPO_ROOT / "ml" / "eval" / hn_file, "r", encoding="utf-8") as f:
            hn_texts = [json.loads(line)["text"] for line in f if line.strip()]
        fp = 0
        for i, t in enumerate(hn_texts):
            res = svc.classify_one(target_id=f"{hn_name}-{i}", target_type="message", raw_text=t, confidence_threshold=0.38)
            if res.is_disinformation:
                fp += 1
        cp_l, cp_h = clopper_pearson_ci(fp, len(hn_texts))
        hybrid_results["hard_negatives"][hn_name] = {
            "fp": fp,
            "n": len(hn_texts),
            "fpr": round(fp / len(hn_texts), 4),
            "clopper_pearson_95_ci": [cp_l, cp_h],
        }

    # 2. Evaluate Step 2.5 SimilarityService (Dense Default vs Lexicon Fallback)
    out_path = REPO_ROOT / "ml" / "reports" / "round2_hybrid_and_similarity.json"
    if "--hybrid-only" in sys.argv and out_path.exists():
        with open(out_path, "r", encoding="utf-8") as f:
            prev = json.load(f)
        sim_step25 = prev.get("step25_similarity_service", {})
    else:
        normaliser = TextNormaliser()
        pairs_path = REPO_ROOT / "ml" / "eval" / "pairs_eval.jsonl"
        clusters_path = REPO_ROOT / "ml" / "eval" / "clusters_eval.jsonl"

        sim_step25: dict[str, Any] = {}
        for label, use_dense in [
            ("Dense Default (SentenceTransformerEmbedder: paraphrase-multilingual-MiniLM-L12-v2)", True),
            ("Lexicon Fallback (DeterministicMultilingualEmbedder)", False),
        ]:
            sim_svc = SimilarityService(use_dense_embedder=use_dense)
            # Warmup encoder load
            _ = sim_svc._embedder.embed("Warmup text")

            t0 = time.perf_counter()
            pair_metrics, _, _ = evaluate_similarity(pairs_path, normaliser, sim_svc, threshold=0.82)
            pair_elapsed = max(1e-6, time.perf_counter() - t0)

            db_mem = DatabaseManager(":memory:")
            db_mem.run_migrations()
            clust_svc = ClusteringService(
                message_repo=SqliteMessageRepository(db_mem),
                cluster_repo=SqliteClusterRepository(db_mem),
                param_repo=SqliteParameterRepository(db_mem),
                similarity_service=sim_svc,
            )
            t1 = time.perf_counter()
            clust_metrics, _, _ = evaluate_clusters(clusters_path, sim_svc, clust_svc, normaliser)
            clust_elapsed = max(1e-6, time.perf_counter() - t1)

            sim_step25[label] = {
                "pairs_eval": {
                    **pair_metrics,
                    "pairs_per_sec": round(317 / pair_elapsed, 1),
                    "elapsed_sec": round(pair_elapsed, 3),
                },
                "clusters_eval": {
                    **clust_metrics,
                    "elapsed_sec": round(clust_elapsed, 3),
                },
            }

    out = {"fixed_hybrid_narrative_service": hybrid_results, "step25_similarity_service": sim_step25}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"[OK] Saved to {out_path}")


if __name__ == "__main__":
    main()
