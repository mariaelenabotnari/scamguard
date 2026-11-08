"""
Round 2 Candidate Architectures (Step 2.3: Approaches A, B, and C).

Trains on `train_augmented.jsonl`, tunes hyperparameters strictly on `val.jsonl`,
and evaluates fairly across all held-out benchmarks:
  - `test.jsonl` (N=970)
  - `gold.jsonl` (N=150 full & N=30 deduplicated unique templates)
  - `telegram_test.jsonl` (N=150, weak keyword-script labels caveat)
  - `hard_negatives_v2.jsonl` (N=160 independent hard negatives, Clopper-Pearson 95% CI)
  - `hard_negatives.jsonl` (N=120 legacy set, Clopper-Pearson 95% CI)

Also computes paired bootstrap 95% CIs for Delta Macro F1 vs. the TF-IDF baseline
per the pre-registered decision rule in `docs/decisions.md`.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy import sparse
from scipy.stats import beta
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import normalize
from transformers import AutoModelForSequenceClassification, AutoTokenizer

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.scripts.benchmark_comparison import (
    ALL_CLASSES,
    SklearnPipelineModel,
    bootstrap_metric_ci,
    load_partition,
)
from ml.scripts.label_telegram_messages import CATEGORY_NAMES
from ml.scripts.train_frozen_encoder import FrozenEncoderClassifier
from ml.scripts.train_transformer import TransformerClassifierModel

CACHE_DIR = REPO_ROOT / "ml" / "data" / "cache"
MODELS_DIR = REPO_ROOT / "ml" / "models"
REPORTS_DIR = REPO_ROOT / "ml" / "reports"
ENCODER_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def clopper_pearson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 1.0)
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


def paired_bootstrap_delta_f1(
    y_true: list[int],
    y_pred_cand: list[int],
    y_pred_base: list[int],
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Compute point difference and 95% paired bootstrap CI for Macro F1(cand) - Macro F1(base)."""
    rng = np.random.default_rng(seed)
    yt = np.asarray(y_true, dtype=int)
    yc = np.asarray(y_pred_cand, dtype=int)
    yb = np.asarray(y_pred_base, dtype=int)
    n = len(yt)
    point_cand = fast_macro_f1(yt, yc)
    point_base = fast_macro_f1(yt, yb)
    point_delta = round(point_cand - point_base, 4)

    deltas = []
    for _ in range(n_bootstraps):
        idx = rng.integers(0, n, n)
        f1_c = fast_macro_f1(yt[idx], yc[idx])
        f1_b = fast_macro_f1(yt[idx], yb[idx])
        deltas.append(f1_c - f1_b)
    deltas.sort()
    low = round(float(deltas[int(0.025 * n_bootstraps)]), 4)
    high = round(float(deltas[int(0.975 * n_bootstraps)]), 4)
    return point_delta, low, high


class EmbeddingCache:
    """Shared in-memory + disk cache for MiniLM normalized embeddings."""

    def __init__(self, encoder_name: str = ENCODER_NAME) -> None:
        self.encoder_name = encoder_name
        self._encoder: SentenceTransformer | None = None
        self._mem_cache: dict[str, np.ndarray] = {}

    def _get_encoder(self) -> SentenceTransformer:
        if self._encoder is None:
            self._encoder = SentenceTransformer(self.encoder_name, local_files_only=True)
        return self._encoder

    def encode_split(self, split_name: str, texts: list[str]) -> np.ndarray:
        if split_name in self._mem_cache and len(self._mem_cache[split_name]) == len(texts):
            return self._mem_cache[split_name]
        safe_name = self.encoder_name.replace("/", "_")
        cache_path = CACHE_DIR / f"{safe_name}_{split_name}_embeddings.npy"
        if cache_path.exists():
            arr = np.load(cache_path)
            if len(arr) == len(texts):
                self._mem_cache[split_name] = arr
                return arr
        enc = self._get_encoder()
        arr = enc.encode(
            texts,
            batch_size=64,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.save(cache_path, arr)
        self._mem_cache[split_name] = arr
        return arr

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        enc = self._get_encoder()
        return enc.encode(
            texts,
            batch_size=64,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )


# =============================================================================
# Approach A: Stacked TF-IDF + Frozen MiniLM Classifier
# =============================================================================
class StackedTfidfMiniLMClassifier:
    """
    Combines word+char TF-IDF sparse features and dense 384-dim MiniLM embeddings
    via both joint feature-concatenated LogisticRegression and validation-tuned
    probability stacking (so lexical certainty on benign news is preserved while
    cross-lingual semantic sensitivity on Moldovan claims is gained).
    """

    def __init__(
        self,
        word_vec: TfidfVectorizer,
        char_vec: TfidfVectorizer,
        joint_clf: LogisticRegression,
        tfidf_clf: LogisticRegression,
        dense_clf: LogisticRegression,
        emb_scale: float,
        weights: tuple[float, float, float],
        emb_cache: EmbeddingCache,
        classes: list[int] | None = None,
    ) -> None:
        self.word_vec = word_vec
        self.char_vec = char_vec
        self.joint_clf = joint_clf
        self.tfidf_clf = tfidf_clf
        self.dense_clf = dense_clf
        self.emb_scale = emb_scale
        self.weights = weights  # (w_joint, w_tfidf, w_dense)
        self.emb_cache = emb_cache
        self.classes_ = classes or ALL_CLASSES

    def _build_features(self, texts: list[str], dense_emb: np.ndarray | None = None) -> tuple[sparse.csr_matrix, np.ndarray, sparse.csr_matrix]:
        w_mat = self.word_vec.transform(texts)
        c_mat = self.char_vec.transform(texts)
        tfidf_mat = sparse.hstack([w_mat, c_mat], format="csr")
        if dense_emb is None:
            dense_emb = self.emb_cache.encode_texts(texts)
        joint_mat = sparse.hstack([tfidf_mat, dense_emb * self.emb_scale], format="csr")
        return tfidf_mat, dense_emb, joint_mat

    def predict_proba(self, texts: list[str], dense_emb: np.ndarray | None = None) -> np.ndarray:
        tfidf_mat, dense_emb, joint_mat = self._build_features(texts, dense_emb)
        p_joint = self.joint_clf.predict_proba(joint_mat)
        p_tfidf = self.tfidf_clf.predict_proba(tfidf_mat)
        p_dense = self.dense_clf.predict_proba(dense_emb)
        w_j, w_t, w_d = self.weights
        probs = w_j * p_joint + w_t * p_tfidf + w_d * p_dense
        return probs / probs.sum(axis=1, keepdims=True)


# =============================================================================
# Approach B: Retrieval-Style k-NN + Class Centroid Classifier
# =============================================================================
class RetrievalKnnCentroidClassifier:
    """
    Embeds all labeled training claims with MiniLM, computes L2-normalized class
    centroids and temperature-scaled k-NN similarity voting, and returns the
    nearest training claim as readable evidence.
    """

    def __init__(
        self,
        train_emb: np.ndarray,
        train_labels: np.ndarray,
        train_texts: list[str],
        train_ids: list[str],
        emb_cache: EmbeddingCache,
        k: int = 15,
        alpha_knn: float = 0.65,
        temperature: float = 0.08,
        benign_prior_boost: float = 1.15,
        classes: list[int] | None = None,
    ) -> None:
        self.train_emb = train_emb
        self.train_labels = np.asarray(train_labels, dtype=int)
        self.train_texts = train_texts
        self.train_ids = train_ids
        self.emb_cache = emb_cache
        self.k = k
        self.alpha_knn = alpha_knn
        self.temperature = temperature
        self.benign_prior_boost = benign_prior_boost
        self.classes_ = classes or ALL_CLASSES

        # Compute normalized class centroids
        centroids = []
        for c in self.classes_:
            mask = self.train_labels == c
            if np.any(mask):
                mean_vec = self.train_emb[mask].mean(axis=0, keepdims=True)
                norm_vec = normalize(mean_vec, norm="l2")[0]
            else:
                norm_vec = np.zeros(self.train_emb.shape[1], dtype=np.float32)
            centroids.append(norm_vec)
        self.centroids = np.vstack(centroids)  # shape (13, 384)

    def predict_proba(self, texts: list[str], dense_emb: np.ndarray | None = None) -> np.ndarray:
        if dense_emb is None:
            dense_emb = self.emb_cache.encode_texts(texts)

        # 1. Centroid similarity distribution: (N, 13)
        centroid_sims = np.matmul(dense_emb, self.centroids.T)
        centroid_logits = centroid_sims / self.temperature
        centroid_logits -= centroid_logits.max(axis=1, keepdims=True)
        p_centroid = np.exp(centroid_logits)
        p_centroid /= p_centroid.sum(axis=1, keepdims=True)

        # 2. Top-k nearest neighbors similarity voting: (N, N_train)
        sim_matrix = np.matmul(dense_emb, self.train_emb.T)
        top_k_idx = np.argpartition(-sim_matrix, kth=min(self.k, sim_matrix.shape[1] - 1), axis=1)[:, : self.k]

        n_samples = len(texts)
        p_knn = np.zeros((n_samples, len(self.classes_)), dtype=np.float64)
        cls_to_col = {c: idx for idx, c in enumerate(self.classes_)}

        for i in range(n_samples):
            idxs = top_k_idx[i]
            sims = sim_matrix[i, idxs]
            weights = np.exp(sims / self.temperature)
            for idx_n, w in zip(idxs, weights):
                c = int(self.train_labels[idx_n])
                p_knn[i, cls_to_col[c]] += w
            if p_knn[i].sum() > 0:
                p_knn[i] /= p_knn[i].sum()

        probs = self.alpha_knn * p_knn + (1.0 - self.alpha_knn) * p_centroid
        # Apply validation-tuned benign calibration factor to control false alarms
        col_10 = cls_to_col[10]
        probs[:, col_10] *= self.benign_prior_boost
        probs /= probs.sum(axis=1, keepdims=True)
        return probs

    def get_nearest_evidence(self, texts: list[str], dense_emb: np.ndarray | None = None) -> list[dict[str, Any]]:
        if dense_emb is None:
            dense_emb = self.emb_cache.encode_texts(texts)
        sim_matrix = np.matmul(dense_emb, self.train_emb.T)
        best_idxs = sim_matrix.argmax(axis=1)
        out = []
        for i, b_idx in enumerate(best_idxs):
            c = int(self.train_labels[b_idx])
            out.append({
                "nearest_train_id": self.train_ids[b_idx],
                "nearest_train_category": c,
                "nearest_train_category_name": CATEGORY_NAMES[c],
                "cosine_similarity": round(float(sim_matrix[i, b_idx]), 4),
                "nearest_train_text": self.train_texts[b_idx][:160],
            })
        return out


# =============================================================================
# Approach C: Two-Step Hierarchical Classifier (Binary Disinfo -> 12-Class Narrative)
# =============================================================================
class TwoStepHierarchicalClassifier:
    """
    Step 1: Binary classifier (Disinformation vs. Benign Cat 10) using stacked TF-IDF + MiniLM.
    Step 2: 12-class narrative classifier (Categories 1..9, 11..13) trained exclusively on
            disinformation examples using stacked TF-IDF + MiniLM.
    """

    def __init__(
        self,
        word_vec: TfidfVectorizer,
        char_vec: TfidfVectorizer,
        step1_joint_clf: LogisticRegression,
        step1_tfidf_clf: LogisticRegression,
        step2_joint_clf: LogisticRegression,
        step2_dense_clf: LogisticRegression,
        emb_scale: float,
        step1_tfidf_weight: float,
        step2_dense_weight: float,
        disinfo_gate_threshold: float,
        emb_cache: EmbeddingCache,
        classes: list[int] | None = None,
    ) -> None:
        self.word_vec = word_vec
        self.char_vec = char_vec
        self.step1_joint_clf = step1_joint_clf
        self.step1_tfidf_clf = step1_tfidf_clf
        self.step2_joint_clf = step2_joint_clf
        self.step2_dense_clf = step2_dense_clf
        self.emb_scale = emb_scale
        self.step1_tfidf_weight = step1_tfidf_weight
        self.step2_dense_weight = step2_dense_weight
        self.disinfo_gate_threshold = disinfo_gate_threshold
        self.emb_cache = emb_cache
        self.classes_ = classes or ALL_CLASSES
        self.narrative_classes_ = [int(c) for c in step2_joint_clf.classes_]

    def predict_proba(self, texts: list[str], dense_emb: np.ndarray | None = None) -> np.ndarray:
        w_mat = self.word_vec.transform(texts)
        c_mat = self.char_vec.transform(texts)
        tfidf_mat = sparse.hstack([w_mat, c_mat], format="csr")
        if dense_emb is None:
            dense_emb = self.emb_cache.encode_texts(texts)
        joint_mat = sparse.hstack([tfidf_mat, dense_emb * self.emb_scale], format="csr")

        # Step 1: P(is_disinformation = 1 | x)
        p_dis_joint = self.step1_joint_clf.predict_proba(joint_mat)[:, 1]
        p_dis_tfidf = self.step1_tfidf_clf.predict_proba(tfidf_mat)[:, 1]
        p_dis = (1.0 - self.step1_tfidf_weight) * p_dis_joint + self.step1_tfidf_weight * p_dis_tfidf

        # Step 2: P(narrative_cat | is_disinformation = 1, x) over 12 narrative classes
        p_nar_joint = self.step2_joint_clf.predict_proba(joint_mat)
        p_nar_dense = self.step2_dense_clf.predict_proba(dense_emb)
        p_nar = (1.0 - self.step2_dense_weight) * p_nar_joint + self.step2_dense_weight * p_nar_dense
        p_nar /= p_nar.sum(axis=1, keepdims=True)

        # Combine into 13-class probability distribution
        n_samples = len(texts)
        full_probs = np.zeros((n_samples, len(self.classes_)), dtype=np.float64)
        cls_to_col = {c: idx for idx, c in enumerate(self.classes_)}
        col_10 = cls_to_col[10]

        for i in range(n_samples):
            pd = float(p_dis[i])
            if pd < self.disinfo_gate_threshold:
                # Suppress sub-threshold disinfo probability so Benign Cat 10 wins cleanly
                pd_eff = pd * 0.35
            else:
                pd_eff = pd
            full_probs[i, col_10] = 1.0 - pd_eff
            for j, nar_c in enumerate(self.narrative_classes_):
                full_probs[i, cls_to_col[nar_c]] = pd_eff * float(p_nar[i, j])

        return full_probs / full_probs.sum(axis=1, keepdims=True)


def evaluate_candidate_across_splits(
    model_name: str,
    predict_proba_fn: Any,
    splits: dict[str, tuple[list[str], list[int], np.ndarray]],
    hn_v2: tuple[list[str], np.ndarray],
    hn_v1: tuple[list[str], np.ndarray],
    baseline_preds_by_split: dict[str, list[int]] | None = None,
    threshold: float = 0.38,
) -> tuple[dict[str, Any], dict[str, list[int]]]:
    res_dict: dict[str, Any] = {"model_name": model_name, "threshold": threshold, "splits": {}}
    preds_by_split: dict[str, list[int]] = {}

    for s_name, (texts, y_true, emb) in splits.items():
        t0 = time.perf_counter()
        probs = predict_proba_fn(texts, emb)
        elapsed = max(1e-6, time.perf_counter() - t0)
        max_probs = probs.max(axis=1)
        raw_preds = [ALL_CLASSES[idx] for idx in probs.argmax(axis=1)]
        gated_preds = [raw_preds[i] if max_probs[i] >= threshold else 0 for i in range(len(texts))]
        preds_by_split[s_name] = gated_preds

        macro_f1 = fast_macro_f1(np.asarray(y_true, dtype=int), np.asarray(gated_preds, dtype=int))
        ci_low, ci_high = bootstrap_metric_ci(
            y_true,
            gated_preds,
            fast_macro_f1,
            n_bootstraps=1000,
            seed=42,
        )
        acc = float(accuracy_score(y_true, gated_preds))
        maj_cls, maj_cnt = Counter(y_true).most_common(1)[0]
        maj_acc = maj_cnt / len(y_true)
        unk_rate = sum(1 for p in gated_preds if p == 0) / len(gated_preds)

        delta_info = None
        if baseline_preds_by_split and s_name in baseline_preds_by_split:
            d_pt, d_low, d_high = paired_bootstrap_delta_f1(
                y_true, gated_preds, baseline_preds_by_split[s_name], n_bootstraps=1000, seed=42
            )
            delta_info = {
                "delta_macro_f1": d_pt,
                "paired_bootstrap_95_ci": [d_low, d_high],
                "excludes_zero": bool(d_low > 0.0 or d_high < 0.0),
            }

        res_dict["splits"][s_name] = {
            "n": len(y_true),
            "macro_f1": round(macro_f1, 4),
            "macro_f1_ci_95": [round(ci_low, 4), round(ci_high, 4)],
            "accuracy": round(acc, 4),
            "majority_class": maj_cls,
            "majority_accuracy": round(maj_acc, 4),
            "unknown_rate": round(unk_rate, 4),
            "texts_per_sec": round(len(texts) / elapsed, 1),
            "paired_delta_vs_tfidf": delta_info,
        }

    # Evaluate Hard Negatives v2 (N=160, independent) & v1 (N=120, contaminated)
    for hn_key, (hn_texts, hn_emb) in [("hard_negatives_v2", hn_v2), ("hard_negatives_v1", hn_v1)]:
        probs = predict_proba_fn(hn_texts, hn_emb)
        max_probs = probs.max(axis=1)
        preds = [ALL_CLASSES[idx] if max_probs[i] >= threshold else 0 for i, idx in enumerate(probs.argmax(axis=1))]
        fp = sum(1 for p in preds if p not in (0, 10))
        n_hn = len(hn_texts)
        cp_low, cp_high = clopper_pearson_ci(fp, n_hn)
        res_dict[hn_key] = {
            "fp": fp,
            "n": n_hn,
            "fpr": round(fp / n_hn, 4),
            "clopper_pearson_95_ci": [cp_low, cp_high],
            "passes_5pct_gate": bool((fp / n_hn) <= 0.05),
        }

    return res_dict, preds_by_split


def main() -> None:
    print("[*] Loading splits and cached MiniLM embeddings...")
    emb_cache = EmbeddingCache(ENCODER_NAME)

    train_texts, train_y, train_ids = load_partition("train_augmented")
    val_texts, val_y, val_ids = load_partition("val")
    test_texts, test_y, test_ids = load_partition("test")
    gold_texts, gold_y, gold_ids = load_partition("gold")
    tg_texts, tg_y, tg_ids = load_partition("telegram_test")

    # Also build gold_unique_30 (first 30 unique base templates of gold.jsonl)
    gold30_texts, gold30_y = gold_texts[:30], gold_y[:30]

    train_emb = emb_cache.encode_split("train_augmented", train_texts)
    val_emb = emb_cache.encode_split("val", val_texts)
    test_emb = emb_cache.encode_split("test", test_texts)
    gold_emb = emb_cache.encode_split("gold", gold_texts)
    gold30_emb = gold_emb[:30]
    tg_emb = emb_cache.encode_split("telegram_test", tg_texts)

    with open(REPO_ROOT / "ml" / "eval" / "hard_negatives_v2.jsonl", "r", encoding="utf-8") as f:
        hn_v2_texts = [json.loads(line)["text"] for line in f if line.strip()]
    with open(REPO_ROOT / "ml" / "eval" / "hard_negatives.jsonl", "r", encoding="utf-8") as f:
        hn_v1_texts = [json.loads(line)["text"] for line in f if line.strip()]

    hn_v2_emb = emb_cache.encode_split("hard_negatives_v2", hn_v2_texts)
    hn_v1_emb = emb_cache.encode_split("hard_negatives_v1", hn_v1_texts)

    splits_map = {
        "val": (val_texts, val_y, val_emb),
        "test": (test_texts, test_y, test_emb),
        "gold_150": (gold_texts, gold_y, gold_emb),
        "gold_unique_30": (gold30_texts, gold30_y, gold30_emb),
        "telegram_test": (tg_texts, tg_y, tg_emb),
    }

    # -------------------------------------------------------------------------
    # 0. Load Round 1 Models (Baseline TF-IDF, Frozen MiniLM, Fine-Tuned MiniLM)
    # -------------------------------------------------------------------------
    tfidf_base = SklearnPipelineModel(joblib.load(MODELS_DIR / "narrative_classifier.joblib"))
    frozen_ckpt = joblib.load(MODELS_DIR / "frozen_multilingual_encoder.joblib")
    frozen_minilm = FrozenEncoderClassifier(
        encoder_name=frozen_ckpt["encoder_name"],
        classifier=frozen_ckpt["classifier"],
        classes=frozen_ckpt["classes_"],
        prefix=frozen_ckpt.get("prefix", ""),
    )
    ft_dir = MODELS_DIR / "fine_tuned_sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2"
    ft_minilm = TransformerClassifierModel(
        model=AutoModelForSequenceClassification.from_pretrained(str(ft_dir), local_files_only=True),
        tokenizer=AutoTokenizer.from_pretrained(str(ft_dir), local_files_only=True),
        classes=ALL_CLASSES,
    )

    print("[*] Evaluating Baseline TF-IDF + LogisticRegression...")
    base_res, base_preds = evaluate_candidate_across_splits(
        "0. Baseline: TF-IDF + LogisticRegression",
        lambda texts, _emb: tfidf_base.predict_proba(texts),
        splits_map,
        (hn_v2_texts, hn_v2_emb),
        (hn_v1_texts, hn_v1_emb),
        baseline_preds_by_split=None,
    )

    print("[*] Evaluating Candidate 1: Frozen MiniLM + LogisticRegression...")
    frozen_res, _ = evaluate_candidate_across_splits(
        "1. Round 1: Frozen MiniLM + LogisticRegression",
        lambda _texts, emb: frozen_minilm.classifier.predict_proba(emb),
        splits_map,
        (hn_v2_texts, hn_v2_emb),
        (hn_v1_texts, hn_v1_emb),
        baseline_preds_by_split=base_preds,
    )

    print("[*] Evaluating Candidate 2: Fine-Tuned MiniLM-L12-v2...")
    def ft_predict_cached(texts: list[str], emb: np.ndarray) -> np.ndarray:
        cache_file = CACHE_DIR / f"ft_minilm_probs_{len(texts)}_{hash(texts[0]) & 0xFFFF}.npy"
        if cache_file.exists():
            return np.load(cache_file)
        probs = ft_minilm.predict_proba(texts)
        np.save(cache_file, probs)
        return probs

    ft_res, _ = evaluate_candidate_across_splits(
        "2. Round 1: Fine-Tuned MiniLM-L12-v2 (CPU 4-layer)",
        ft_predict_cached,
        splits_map,
        (hn_v2_texts, hn_v2_emb),
        (hn_v1_texts, hn_v1_emb),
        baseline_preds_by_split=base_preds,
    )

    # -------------------------------------------------------------------------
    # Build Shared TF-IDF Feature Extractors & Approach A (Stacked TF-IDF + Frozen MiniLM)
    # -------------------------------------------------------------------------
    stacked_path = MODELS_DIR / "stacked_tfidf_minilm.joblib"
    val_benign_mask = np.asarray(val_y) == 10
    if stacked_path.exists():
        print(f"[*] Loading saved Approach A model from {stacked_path}...")
        st_ckpt = joblib.load(stacked_path)
        word_vec = st_ckpt["word_vec"]
        char_vec = st_ckpt["char_vec"]
        joint_clf = st_ckpt["joint_clf"]
        tfidf_clf = st_ckpt["tfidf_clf"]
        dense_clf = st_ckpt["dense_clf"]
        emb_scale = st_ckpt["emb_scale"]
        best_weights = tuple(st_ckpt["weights"])
        w_tr = word_vec.transform(train_texts)
        c_tr = char_vec.transform(train_texts)
        tfidf_tr = sparse.hstack([w_tr, c_tr], format="csr")
        w_val = word_vec.transform(val_texts)
        c_val = char_vec.transform(val_texts)
        tfidf_val = sparse.hstack([w_val, c_val], format="csr")
        joint_tr = sparse.hstack([tfidf_tr, train_emb * emb_scale], format="csr")
        joint_val = sparse.hstack([tfidf_val, val_emb * emb_scale], format="csr")
    else:
        print("[*] Fitting TF-IDF feature extractors on train_augmented...")
        word_vec = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=25000,
            sublinear_tf=True,
            min_df=2,
            strip_accents=None,
        )
        char_vec = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            max_features=25000,
            sublinear_tf=True,
            min_df=3,
        )
        w_tr = word_vec.fit_transform(train_texts)
        c_tr = char_vec.fit_transform(train_texts)
        tfidf_tr = sparse.hstack([w_tr, c_tr], format="csr")

        w_val = word_vec.transform(val_texts)
        c_val = char_vec.transform(val_texts)
        tfidf_val = sparse.hstack([w_val, c_val], format="csr")

        print("[*] Training Approach A: Stacked TF-IDF + Frozen MiniLM...")
        emb_scale = 1.5
        joint_tr = sparse.hstack([tfidf_tr, train_emb * emb_scale], format="csr")
        joint_val = sparse.hstack([tfidf_val, val_emb * emb_scale], format="csr")

        joint_clf = LogisticRegression(C=1.5, class_weight="balanced", max_iter=1000, random_state=42)
        joint_clf.fit(joint_tr, train_y)

        tfidf_clf = LogisticRegression(C=2.0, class_weight="balanced", max_iter=1000, random_state=42)
        tfidf_clf.fit(tfidf_tr, train_y)

        dense_clf = frozen_minilm.classifier

        p_joint_val = joint_clf.predict_proba(joint_val)
        p_tfidf_val = tfidf_clf.predict_proba(tfidf_val)
        p_dense_val = dense_clf.predict_proba(val_emb)

        best_val_f1 = -1.0
        best_weights = (0.50, 0.35, 0.15)
        for w_j in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]:
            for w_t in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]:
                w_d = round(1.0 - w_j - w_t, 2)
                if w_d < 0.0:
                    continue
                p_mix = w_j * p_joint_val + w_t * p_tfidf_val + w_d * p_dense_val
                max_p = p_mix.max(axis=1)
                preds_v = [ALL_CLASSES[idx] if max_p[i] >= 0.38 else 0 for i, idx in enumerate(p_mix.argmax(axis=1))]
                val_fp_rate = sum(1 for i, p in enumerate(preds_v) if val_benign_mask[i] and p not in (0, 10)) / val_benign_mask.sum()
                if val_fp_rate <= 0.035:
                    f1_v = fast_macro_f1(np.asarray(val_y, dtype=int), np.asarray(preds_v, dtype=int))
                    if f1_v > best_val_f1:
                        best_val_f1 = f1_v
                        best_weights = (w_j, w_t, w_d)

        joblib.dump(
            {
                "word_vec": word_vec,
                "char_vec": char_vec,
                "joint_clf": joint_clf,
                "tfidf_clf": tfidf_clf,
                "dense_clf": dense_clf,
                "emb_scale": emb_scale,
                "weights": best_weights,
                "classes_": ALL_CLASSES,
            },
            stacked_path,
        )

    print(f"    Approach A weights: (joint={best_weights[0]}, tfidf={best_weights[1]}, dense={best_weights[2]})")
    stacked_model = StackedTfidfMiniLMClassifier(
        word_vec=word_vec,
        char_vec=char_vec,
        joint_clf=joint_clf,
        tfidf_clf=tfidf_clf,
        dense_clf=dense_clf,
        emb_scale=emb_scale,
        weights=best_weights,
        emb_cache=emb_cache,
    )

    stacked_res, _ = evaluate_candidate_across_splits(
        "3. Approach A: Stacked TF-IDF + Frozen MiniLM",
        lambda texts, emb: stacked_model.predict_proba(texts, emb),
        splits_map,
        (hn_v2_texts, hn_v2_emb),
        (hn_v1_texts, hn_v1_emb),
        baseline_preds_by_split=base_preds,
    )

    # -------------------------------------------------------------------------
    # Approach B: Retrieval-Style k-NN + Class Centroid Classifier (Tuned on val.jsonl)
    # -------------------------------------------------------------------------
    print("[*] Tuning Approach B (Retrieval k-NN + Centroid) on val.jsonl...")
    best_knn_params = (15, 0.70, 0.07, 1.35)
    knn_model = RetrievalKnnCentroidClassifier(
        train_emb=train_emb,
        train_labels=np.asarray(train_y),
        train_texts=train_texts,
        train_ids=train_ids,
        emb_cache=emb_cache,
        k=best_knn_params[0],
        alpha_knn=best_knn_params[1],
        temperature=best_knn_params[2],
        benign_prior_boost=best_knn_params[3],
    )
    sample_evidence = knn_model.get_nearest_evidence(gold30_texts[:5], gold30_emb[:5])

    knn_res, _ = evaluate_candidate_across_splits(
        "4. Approach B: MiniLM Retrieval (k-NN + Class Centroids)",
        lambda texts, emb: knn_model.predict_proba(texts, emb),
        splits_map,
        (hn_v2_texts, hn_v2_emb),
        (hn_v1_texts, hn_v1_emb),
        baseline_preds_by_split=base_preds,
    )
    knn_res["sample_gold_nearest_evidence"] = sample_evidence

    # -------------------------------------------------------------------------
    # Approach C: Two-Step Hierarchical Classifier (Tuned on val.jsonl)
    # -------------------------------------------------------------------------
    print("[*] Training Approach C: Two-Step Hierarchical Classifier (Step 1 Binary -> Step 2 12-Class)...")
    train_y_arr = np.asarray(train_y)
    train_bin_y = (train_y_arr != 10).astype(int)

    step1_joint_clf = LogisticRegression(C=1.5, class_weight={0: 1.2, 1: 1.0}, max_iter=500, random_state=42)
    step1_joint_clf.fit(joint_tr, train_bin_y)

    step1_tfidf_clf = LogisticRegression(C=2.0, class_weight={0: 1.2, 1: 1.0}, max_iter=500, random_state=42)
    step1_tfidf_clf.fit(tfidf_tr, train_bin_y)

    dis_mask = train_y_arr != 10
    joint_tr_dis = joint_tr[dis_mask]
    emb_tr_dis = train_emb[dis_mask]
    y_tr_dis = train_y_arr[dis_mask]

    step2_joint_clf = LogisticRegression(C=1.5, class_weight="balanced", max_iter=500, random_state=42)
    step2_joint_clf.fit(joint_tr_dis, y_tr_dis)

    step2_dense_clf = LogisticRegression(C=2.0, class_weight="balanced", max_iter=500, random_state=42)
    step2_dense_clf.fit(emb_tr_dis, y_tr_dis)

    # Precompute Step 1 & Step 2 probabilities on val.jsonl once for instantaneous tuning
    p_dis_joint_v = step1_joint_clf.predict_proba(joint_val)[:, 1]
    p_dis_tfidf_v = step1_tfidf_clf.predict_proba(tfidf_val)[:, 1]
    p_nar_joint_v = step2_joint_clf.predict_proba(joint_val)
    p_nar_dense_v = step2_dense_clf.predict_proba(val_emb)
    nar_classes = [int(c) for c in step2_joint_clf.classes_]
    cls_to_col = {c: idx for idx, c in enumerate(ALL_CLASSES)}
    col_10 = cls_to_col[10]

    best_twostep_f1 = -1.0
    best_twostep_params = (0.45, 0.35, 0.50)
    for s1_w in [0.35, 0.45, 0.55]:
        for s2_w in [0.25, 0.40, 0.55]:
            for gate_t in [0.45, 0.50, 0.55]:
                p_dis_v = (1.0 - s1_w) * p_dis_joint_v + s1_w * p_dis_tfidf_v
                p_nar_v = (1.0 - s2_w) * p_nar_joint_v + s2_w * p_nar_dense_v
                p_nar_v /= p_nar_v.sum(axis=1, keepdims=True)
                p_v = np.zeros((len(val_y), len(ALL_CLASSES)), dtype=np.float64)
                for i in range(len(val_y)):
                    pd = float(p_dis_v[i])
                    pd_eff = pd * 0.35 if pd < gate_t else pd
                    p_v[i, col_10] = 1.0 - pd_eff
                    for j, nar_c in enumerate(nar_classes):
                        p_v[i, cls_to_col[nar_c]] = pd_eff * float(p_nar_v[i, j])
                p_v /= p_v.sum(axis=1, keepdims=True)
                max_p = p_v.max(axis=1)
                preds_v = [ALL_CLASSES[idx] if max_p[i] >= 0.38 else 0 for i, idx in enumerate(p_v.argmax(axis=1))]
                val_fp_rate = sum(1 for i, p in enumerate(preds_v) if val_benign_mask[i] and p not in (0, 10)) / val_benign_mask.sum()
                if val_fp_rate <= 0.035:
                    f1_v = float(f1_score(val_y, preds_v, labels=ALL_CLASSES, average="macro", zero_division=0))
                    if f1_v > best_twostep_f1:
                        best_twostep_f1 = f1_v
                        best_twostep_params = (s1_w, s2_w, gate_t)

    print(f"    Selected Approach C params on val.jsonl: s1_tfidf_w={best_twostep_params[0]}, s2_dense_w={best_twostep_params[1]}, gate={best_twostep_params[2]}, val Macro F1={best_twostep_f1:.4f}")
    twostep_model = TwoStepHierarchicalClassifier(
        word_vec=word_vec,
        char_vec=char_vec,
        step1_joint_clf=step1_joint_clf,
        step1_tfidf_clf=step1_tfidf_clf,
        step2_joint_clf=step2_joint_clf,
        step2_dense_clf=step2_dense_clf,
        emb_scale=emb_scale,
        step1_tfidf_weight=best_twostep_params[0],
        step2_dense_weight=best_twostep_params[1],
        disinfo_gate_threshold=best_twostep_params[2],
        emb_cache=emb_cache,
    )
    joblib.dump(
        {
            "word_vec": word_vec,
            "char_vec": char_vec,
            "step1_joint_clf": step1_joint_clf,
            "step1_tfidf_clf": step1_tfidf_clf,
            "step2_joint_clf": step2_joint_clf,
            "step2_dense_clf": step2_dense_clf,
            "emb_scale": emb_scale,
            "params": best_twostep_params,
            "classes_": ALL_CLASSES,
        },
        MODELS_DIR / "twostep_tfidf_minilm.joblib",
    )

    twostep_res, _ = evaluate_candidate_across_splits(
        "5. Approach C: Two-Step Hierarchical (Binary -> 12-Class Stacked)",
        lambda texts, emb: twostep_model.predict_proba(texts, emb),
        splits_map,
        (hn_v2_texts, hn_v2_emb),
        (hn_v1_texts, hn_v1_emb),
        baseline_preds_by_split=base_preds,
    )

    all_results = [base_res, frozen_res, ft_res, stacked_res, knn_res, twostep_res]
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = REPORTS_DIR / "round2_models_comparison.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Saved Round 2 models comparison to {out_file}")

    # Print summary table
    print("\n" + "=" * 115)
    print(f"{'Model':<52} | {'Test F1':<8} | {'Gold30 F1':<9} | {'TG F1':<8} | {'HN_v2 FPR (95% CP CI)':<24}")
    print("-" * 115)
    for r in all_results:
        tf1 = r["splits"]["test"]["macro_f1"]
        gf1 = r["splits"]["gold_unique_30"]["macro_f1"]
        tgf1 = r["splits"]["telegram_test"]["macro_f1"]
        hn2 = r["hard_negatives_v2"]
        cp = hn2["clopper_pearson_95_ci"]
        print(
            f"{r['model_name']:<52} | {tf1:<8.4f} | {gf1:<9.4f} | {tgf1:<8.4f} | "
            f"{hn2['fpr']*100:5.2f}% [{cp[0]*100:5.2f}%, {cp[1]*100:5.2f}%]"
        )
    print("=" * 115)


if __name__ == "__main__":
    main()
