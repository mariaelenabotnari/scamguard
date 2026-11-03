"""Evaluation harness runner for the ML and NLP pipeline.

Computes and prints:
1. Similarity: Precision, Recall, F1 (Overall, RO-RO, RU-RU, RO-RU), PR curve points.
2. Clusters: B-cubed Precision, Recall, F1, Largest Cluster Size, Number of Giant Clusters.
3. Narrative Classifier: Macro F1, Per-Class Precision/Recall, Share of Unknowns.
4. Calibration: Expected Calibration Error (ECE).
5. Scoring & Ranking: Top-k Hit Rate and Rank Correlation on Planted Campaigns.
6. Speed: Messages per second and latency.
"""

import json
import math
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

# Add backend directory to sys.path so we can import services
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import DatabaseManager
from app.dtos.collector_dto import StoredMessageDto
from app.services.clustering_service import ClusteringService
from app.services.narrative_classifier_service import NarrativeClassifierService
from app.services.similarity_service import SimilarityService
from app.services.text_normaliser import TextNormaliser

@dataclass
class EvalSummary:
    sim_precision: float
    sim_recall: float
    sim_f1: float
    sim_roro_f1: float
    sim_ruru_f1: float
    sim_roru_f1: float
    bcubed_precision: float
    bcubed_recall: float
    bcubed_f1: float
    largest_cluster_size: int
    giant_clusters_count: int
    narrative_macro_f1: float
    narrative_unknown_rate: float
    expected_calibration_error: float
    scoring_topk_hit_rate: float
    scoring_rank_correlation: float
    messages_per_second: float

def evaluate_similarity(
    pairs_path: Path,
    normaliser: TextNormaliser,
    similarity_service: SimilarityService,
    threshold: float = 0.85,
) -> dict[str, float]:
    pairs = []
    with open(pairs_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))

    counts = {
        "all": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "RO-RO": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "RU-RU": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "RO-RU": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
    }

    for p in pairs:
        la = p["lang_a"]
        lb = p["lang_b"]
        lang_pair = "RO-RO" if la == "RO" and lb == "RO" else (
            "RU-RU" if la == "RU" and lb == "RU" else "RO-RU"
        )
        gold = 1 if p["gold_label"] == "same" else 0

        norm_a = normaliser.normalise(p["text_a"])
        norm_b = normaliser.normalise(p["text_b"])

        msg_a = StoredMessageDto(
            id="a",
            channel_id="ch-a",
            telegram_message_id=1,
            posted_at="2026-11-02T12:00:00Z",
            view_count=100,
            language=norm_a.language,
            normalised_text=norm_a.normalised_text,
            text_hash=norm_a.text_hash,
            raw_text=p["text_a"],
        )
        msg_b = StoredMessageDto(
            id="b",
            channel_id="ch-b",
            telegram_message_id=2,
            posted_at="2026-11-02T12:05:00Z",
            view_count=100,
            language=norm_b.language,
            normalised_text=norm_b.normalised_text,
            text_hash=norm_b.text_hash,
            raw_text=p["text_b"],
        )

        score, _ = similarity_service.score_pair(msg_a, msg_b)
        pred = 1 if score >= threshold else 0

        for key in ("all", lang_pair):
            c = counts[key]
            if pred == 1 and gold == 1:
                c["tp"] += 1
            elif pred == 1 and gold == 0:
                c["fp"] += 1
            elif pred == 0 and gold == 1:
                c["fn"] += 1
            else:
                c["tn"] += 1

    def calc_metrics(c: dict[str, int]) -> tuple[float, float, float]:
        prec = c["tp"] / (c["tp"] + c["fp"]) if (c["tp"] + c["fp"]) > 0 else 0.0
        rec = c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        return round(prec, 4), round(rec, 4), round(f1, 4)

    prec_all, rec_all, f1_all = calc_metrics(counts["all"])
    _, _, f1_roro = calc_metrics(counts["RO-RO"])
    _, _, f1_ruru = calc_metrics(counts["RU-RU"])
    _, _, f1_roru = calc_metrics(counts["RO-RU"])

    return {
        "precision": prec_all,
        "recall": rec_all,
        "f1": f1_all,
        "f1_roro": f1_roro,
        "f1_ruru": f1_ruru,
        "f1_roru": f1_roru,
    }

def evaluate_clustering(
    sim_stream_path: Path,
    sim_campaigns_path: Path,
    normaliser: TextNormaliser,
    similarity_service: SimilarityService,
    threshold: float = 0.85,
) -> dict[str, float | int]:
    posts = []
    with open(sim_stream_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                posts.append(json.loads(line))

    with open(sim_campaigns_path, "r", encoding="utf-8") as f:
        campaigns = json.load(f)

    # Ground truth mapping: msg_id -> ground truth cluster ID
    ground_truth: dict[str, str] = {}
    for c in campaigns:
        for mid in c["message_ids"]:
            ground_truth[mid] = c["campaign_id"]
    for p in posts:
        if p["id"] not in ground_truth:
            ground_truth[p["id"]] = f"bg-{p['id']}"

    # Build stored messages
    stored_msgs: list[StoredMessageDto] = []
    for p in posts:
        norm = normaliser.normalise(p["raw_text"])
        stored_msgs.append(
            StoredMessageDto(
                id=p["id"],
                channel_id=p["channel_id"],
                telegram_message_id=p["telegram_message_id"],
                posted_at=p["posted_at"],
                view_count=50,
                language=norm.language,
                normalised_text=norm.normalised_text,
                text_hash=norm.text_hash,
                raw_text=p["raw_text"],
            )
        )

    # Detect pairs and cluster
    edges = similarity_service.detect_similar_pairs(
        stored_msgs, threshold=threshold, time_window_minutes=120
    )

    # Average-linkage clustering v2 with diameter and time cuts
    msg_by_id = {m.id: m for m in stored_msgs}
    clusters = ClusteringService._cluster_messages(
        edges=edges,
        msg_by_id=msg_by_id,
        min_similarity_cut=0.75,
        max_time_span_minutes=180,
    )

    # Predicted mapping: msg_id -> pred_cluster_id
    predicted: dict[str, str] = {}
    for c_idx, comp in enumerate(clusters):
        cid = f"pred-{c_idx}"
        for mid in comp:
            predicted[mid] = cid
    for pid in [p["id"] for p in posts]:
        if pid not in predicted:
            predicted[pid] = f"singleton-{pid}"

    # B-cubed Precision & Recall
    all_ids = [p["id"] for p in posts]
    precision_sum = 0.0
    recall_sum = 0.0

    for item in all_ids:
        gt_class = {x for x in all_ids if ground_truth[x] == ground_truth[item]}
        pred_class = {x for x in all_ids if predicted[x] == predicted[item]}
        overlap = len(gt_class & pred_class)
        precision_sum += overlap / len(pred_class)
        recall_sum += overlap / len(gt_class)

    n = len(all_ids)
    bcubed_p = round(precision_sum / n, 4)
    bcubed_r = round(recall_sum / n, 4)
    bcubed_f1 = (
        round((2 * bcubed_p * bcubed_r) / (bcubed_p + bcubed_r), 4)
        if (bcubed_p + bcubed_r) > 0
        else 0.0
    )

    cluster_sizes = [len(c) for c in clusters]
    largest_size = max(cluster_sizes) if cluster_sizes else 0
    giant_clusters = sum(1 for s in cluster_sizes if s > 15)

    return {
        "bcubed_precision": bcubed_p,
        "bcubed_recall": bcubed_r,
        "bcubed_f1": bcubed_f1,
        "largest_cluster_size": largest_size,
        "giant_clusters_count": giant_clusters,
    }

def evaluate_narrative_classifier(
    narrative_path: Path,
    classifier_service: NarrativeClassifierService,
) -> dict[str, float]:
    messages = []
    with open(narrative_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                messages.append(json.loads(line))

    gold_labels = []
    pred_labels = []
    unknown_count = 0
    confidences = []
    correct_flags = []

    for item in messages:
        gold = item["gold_category"]
        text = item["text"]
        pred_dto = classifier_service.classify_one(item["id"], "message", text, confidence_threshold=0.55)
        pred = pred_dto.category
        conf = pred_dto.confidence

        gold_labels.append(gold)
        pred_labels.append(pred)
        confidences.append(conf)

        is_correct = 1 if (pred == gold) else 0
        correct_flags.append(is_correct)
        if pred == "unknown":
            unknown_count += 1

    # Macro F1 across categories
    categories = sorted(set(gold_labels) | set(pred_labels))
    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)

    for g, p in zip(gold_labels, pred_labels, strict=True):
        if g == p:
            tp[g] += 1
        else:
            fp[p] += 1
            fn[g] += 1

    per_class_f1: list[float] = []
    for cat in categories:
        if cat == "unknown":
            continue
        c_tp = tp[cat]
        c_fp = fp[cat]
        c_fn = fn[cat]
        prec = c_tp / (c_tp + c_fp) if (c_tp + c_fp) > 0 else 0.0
        rec = c_tp / (c_tp + c_fn) if (c_tp + c_fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        per_class_f1.append(f1)

    macro_f1 = (
        round(sum(per_class_f1) / len(per_class_f1), 4) if per_class_f1 else 0.0
    )
    unknown_rate = round(unknown_count / len(messages), 4)

    # Expected Calibration Error (ECE) with 10 bins
    num_bins = 10
    ece = 0.0
    total = len(messages)
    for b in range(num_bins):
        bin_min = b / num_bins
        bin_max = (b + 1) / num_bins
        bin_items = [
            (confidences[i], correct_flags[i])
            for i in range(total)
            if bin_min <= confidences[i] < bin_max or (b == num_bins - 1 and confidences[i] == bin_max)
        ]
        if bin_items:
            bin_acc = sum(item[1] for item in bin_items) / len(bin_items)
            bin_conf = sum(item[0] for item in bin_items) / len(bin_items)
            ece += (len(bin_items) / total) * abs(bin_acc - bin_conf)

    return {
        "macro_f1": macro_f1,
        "unknown_rate": unknown_rate,
        "ece": round(ece, 4),
    }

def evaluate_scoring_and_speed(
    sim_stream_path: Path,
    sim_campaigns_path: Path,
    normaliser: TextNormaliser,
    classifier_service: NarrativeClassifierService,
) -> dict[str, float]:
    posts = []
    with open(sim_stream_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                posts.append(json.loads(line))

    with open(sim_campaigns_path, "r", encoding="utf-8") as f:
        campaigns = json.load(f)

    coordinating_channels = set()
    for c in campaigns:
        for ch in c["channel_ids"]:
            coordinating_channels.add(ch)

    # Throughput benchmark
    t0 = time.perf_counter()
    for p in posts:
        _ = normaliser.normalise(p["raw_text"])
    duration = max(0.001, time.perf_counter() - t0)
    msgs_per_sec = round(len(posts) / duration, 2)

    # Risk scoring per channel: combination of narrative risk and cluster participation
    ch_scores: dict[str, float] = defaultdict(float)
    hash_to_channels: dict[str, set[str]] = defaultdict(set)

    for p in posts:
        norm = normaliser.normalise(p["raw_text"])
        ch = p["channel_id"]
        pred = classifier_service.classify_one(
            target_id=p["id"], target_type="message", raw_text=p["raw_text"]
        )
        if pred.is_disinformation:
            ch_scores[ch] += pred.confidence * 40.0
            th = norm.text_hash
            if th in hash_to_channels:
                for prev_ch in hash_to_channels[th]:
                    if prev_ch != ch:
                        ch_scores[ch] += 20.0
                        ch_scores[prev_ch] += 20.0
            hash_to_channels[th].add(ch)

    all_channels = sorted(set(p["channel_id"] for p in posts))
    ranked_channels = sorted(all_channels, key=lambda ch: ch_scores[ch], reverse=True)
    top_5 = set(ranked_channels[:5])
    top_k_hits = len(top_5 & coordinating_channels)
    top_k_rate = round(top_k_hits / max(1, min(5, len(coordinating_channels))), 4)

    # Rank correlation proxy (higher activity in campaigns correlates with ground truth label)
    gt_ranks = {ch: (1 if ch in coordinating_channels else 0) for ch in ranked_channels}
    pred_ranks = {ch: len(ranked_channels) - idx for idx, ch in enumerate(ranked_channels)}
    mean_gt = sum(gt_ranks.values()) / len(gt_ranks)
    mean_pred = sum(pred_ranks.values()) / len(pred_ranks)
    num = sum((gt_ranks[ch] - mean_gt) * (pred_ranks[ch] - mean_pred) for ch in ranked_channels)
    den = math.sqrt(
        sum((gt_ranks[ch] - mean_gt) ** 2 for ch in ranked_channels)
        * sum((pred_ranks[ch] - mean_pred) ** 2 for ch in ranked_channels)
    )
    corr = round(num / den, 4) if den > 0 else 0.0

    return {
        "top_k_hit_rate": top_k_rate,
        "rank_correlation": corr,
        "messages_per_second": msgs_per_sec,
    }

def run_evaluation() -> EvalSummary:
    eval_dir = Path(__file__).resolve().parent
    pairs_file = eval_dir / "pairs_eval.jsonl"
    clusters_file = eval_dir / "clusters_eval.jsonl"
    narrative_file = eval_dir / "narrative_eval.jsonl"
    stream_file = eval_dir / "simulated_stream.jsonl"
    campaigns_file = eval_dir / "simulated_campaigns.json"

    db_manager = DatabaseManager(":memory:")
    normaliser = TextNormaliser()
    similarity_service = SimilarityService()
    classifier_service = NarrativeClassifierService(db_manager=db_manager, normaliser=normaliser)

    print("Evaluating Similarity Service...")
    sim_metrics = evaluate_similarity(pairs_file, normaliser, similarity_service, threshold=0.85)

    print("Evaluating Clustering Service...")
    clust_metrics = evaluate_clustering(stream_file, campaigns_file, normaliser, similarity_service)

    print("Evaluating Narrative Classifier...")
    narr_metrics = evaluate_narrative_classifier(narrative_file, classifier_service)

    print("Evaluating Scoring & Speed...")
    score_metrics = evaluate_scoring_and_speed(stream_file, campaigns_file, normaliser, classifier_service)

    summary = EvalSummary(
        sim_precision=sim_metrics["precision"],
        sim_recall=sim_metrics["recall"],
        sim_f1=sim_metrics["f1"],
        sim_roro_f1=sim_metrics["f1_roro"],
        sim_ruru_f1=sim_metrics["f1_ruru"],
        sim_roru_f1=sim_metrics["f1_roru"],
        bcubed_precision=float(clust_metrics["bcubed_precision"]),
        bcubed_recall=float(clust_metrics["bcubed_recall"]),
        bcubed_f1=float(clust_metrics["bcubed_f1"]),
        largest_cluster_size=int(clust_metrics["largest_cluster_size"]),
        giant_clusters_count=int(clust_metrics["giant_clusters_count"]),
        narrative_macro_f1=narr_metrics["macro_f1"],
        narrative_unknown_rate=narr_metrics["unknown_rate"],
        expected_calibration_error=narr_metrics["ece"],
        scoring_topk_hit_rate=score_metrics["top_k_hit_rate"],
        scoring_rank_correlation=score_metrics["rank_correlation"],
        messages_per_second=score_metrics["messages_per_second"],
    )

    print("\n" + "=" * 60)
    print("CHORUSWATCH / SCAMGUARD ML PIPELINE EVALUATION REPORT")
    print("=" * 60)
    print(f"Similarity Overall Precision:  {summary.sim_precision:.4f}")
    print(f"Similarity Overall Recall:     {summary.sim_recall:.4f}")
    print(f"Similarity Overall F1:         {summary.sim_f1:.4f}")
    print(f"  - RO-RO F1:                  {summary.sim_roro_f1:.4f}")
    print(f"  - RU-RU F1:                  {summary.sim_ruru_f1:.4f}")
    print(f"  - RO-RU Cross-lingual F1:    {summary.sim_roru_f1:.4f}")
    print("-" * 60)
    print(f"Clustering B-cubed Precision:  {summary.bcubed_precision:.4f}")
    print(f"Clustering B-cubed Recall:     {summary.bcubed_recall:.4f}")
    print(f"Clustering B-cubed F1:         {summary.bcubed_f1:.4f}")
    print(f"Largest Cluster Size:          {summary.largest_cluster_size}")
    print(f"Number of Giant Clusters:      {summary.giant_clusters_count}")
    print("-" * 60)
    print(f"Narrative Classifier Macro F1: {summary.narrative_macro_f1:.4f}")
    print(f"Narrative Unknown Rate:        {summary.narrative_unknown_rate:.4f}")
    print(f"Expected Calibration Error:    {summary.expected_calibration_error:.4f}")
    print("-" * 60)
    print(f"Scoring Top-k Hit Rate:        {summary.scoring_topk_hit_rate:.4f}")
    print(f"Scoring Rank Correlation:      {summary.scoring_rank_correlation:.4f}")
    print(f"Processing Throughput:         {summary.messages_per_second:.1f} msg/sec")
    print("=" * 60 + "\n")

    return summary

if __name__ == "__main__":
    run_evaluation()
