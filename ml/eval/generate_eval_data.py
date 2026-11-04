"""
Generate evaluation datasets for ScamGuard ML evaluation harness.
Builds strictly from authentic collected corpora:
  - ml/data/processed/v1/{test,gold,train,val}.jsonl

Outputs:
  - ml/eval/pairs_eval.jsonl (320+ balanced pairs: exact, edit, rewrite, translation, detail-altered, negation-altered, same-topic different-claim, unrelated)
  - ml/eval/clusters_eval.jsonl (35+ multi-channel cascades with known ground truth)
  - ml/eval/hard_negatives.jsonl (100+ neutral news mentioning sensitive entities: EU, NATO, elections, tariffs, banks)
"""

import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

random.seed(42)

ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_V1 = ROOT_DIR / "ml" / "data" / "processed" / "v1"
EVAL_DIR = ROOT_DIR / "ml" / "eval"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    if not path.exists():
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def build_hard_negatives(records: List[Dict[str, Any]], target_count: int = 120) -> List[Dict[str, Any]]:
    sensitive_keywords = [
        "ue", "uniunea europeana", "bruxelles", "nato", "alegeri", "vot", "guvern",
        "parlament", "gaz", "energie", "tarif", "banca", "transnistria", "gagauzia",
        "ес", "евросоюз", "нато", "выборы", "правительство", "газ", "тариф", "банк"
    ]
    negatives = []
    for r in records:
        if r.get("primary_label") == 10:
            text_lower = r["text"].lower()
            if any(re.search(rf"\b{re.escape(kw)}\b", text_lower) for kw in sensitive_keywords):
                negatives.append({
                    "id": f"hard-neg-{len(negatives)+1:04d}",
                    "text": r["text"],
                    "language": r.get("language", "ro"),
                    "primary_label": 10,
                    "is_disinformation": False,
                    "source": r.get("source_name", "MOROCO/Gazeta"),
                    "matched_topic": next(kw for kw in sensitive_keywords if kw in text_lower)
                })
                if len(negatives) >= target_count:
                    break
    return negatives


def build_pairs_eval(all_recs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    pairs = []
    disinfo_recs = [r for r in all_recs if r.get("is_disinformation") and len(r["text"]) > 35]
    benign_recs = [r for r in all_recs if not r.get("is_disinformation")]

    # 1. Exact copy pairs (50 pairs)
    for r in disinfo_recs[:50]:
        lang = "RO" if r["language"] == "ro" else "RU"
        pairs.append({
            "pair_type": "exact_copy",
            "lang_a": lang,
            "lang_b": lang,
            "text_a": r["text"],
            "text_b": r["text"],
            "gold_label": "same",
            "notes": "Authentic claim duplicated identically"
        })

    # 2. Lightly edited pairs (50 pairs)
    for r in disinfo_recs[50:100]:
        lang = "RO" if r["language"] == "ro" else "RU"
        t_a = r["text"]
        prefix = "⚡ URGENT: " if lang == "RO" else "⚡ СРОЧНО: "
        t_b = f"{prefix}{t_a.rstrip('.')}! 👉 Detalii pe canal."
        pairs.append({
            "pair_type": "lightly_edited",
            "lang_a": lang,
            "lang_b": lang,
            "text_a": t_a,
            "text_b": t_b,
            "gold_label": "same",
            "notes": "Authentic claim with typical Telegram channel formatting"
        })

    # 3. Cross-lingual translation pairs (50 pairs)
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in all_recs:
        gid = r.get("group_id")
        if gid:
            groups.setdefault(gid, []).append(r)

    cross_count = 0
    for gid, members in groups.items():
        ro_m = [m for m in members if m["language"] == "ro"]
        ru_m = [m for m in members if m["language"] == "ru"]
        if ro_m and ru_m:
            pairs.append({
                "pair_type": "translated_ro_ru",
                "lang_a": "RO",
                "lang_b": "RU",
                "text_a": ro_m[0]["text"],
                "text_b": ru_m[0]["text"],
                "gold_label": "same",
                "notes": f"Cross-lingual translations bound by group_id {gid}"
            })
            cross_count += 1
            if cross_count >= 50:
                break

    # 4. Detail-altered pairs (50 pairs: numbers and dates altered)
    detail_count = 0
    for r in disinfo_recs[100:]:
        text = r["text"]
        nums = re.findall(r"\b\d+\b", text)
        if nums:
            old_num = nums[0]
            new_num = str(int(old_num) * 3 + 12)
            t_alt = re.sub(rf"\b{old_num}\b", new_num, text, count=1)
            lang = "RO" if r["language"] == "ro" else "RU"
            pairs.append({
                "pair_type": "detail_altered_number",
                "lang_a": lang,
                "lang_b": lang,
                "text_a": text,
                "text_b": t_alt,
                "gold_label": "different",
                "notes": f"Changed key numerical fact ({old_num} -> {new_num})"
            })
            detail_count += 1
            if detail_count >= 50:
                break

    # 5. Negation-altered pairs (50 pairs: polarity toggled)
    neg_count = 0
    for r in disinfo_recs[150:]:
        text = r["text"]
        lang = "RO" if r["language"] == "ro" else "RU"
        if lang == "RO" and " va " in text:
            t_neg = text.replace(" va ", " nu va ", 1)
        elif lang == "RO" and " este " in text:
            t_neg = text.replace(" este ", " nu este ", 1)
        elif lang == "RU" and " будет " in text:
            t_neg = text.replace(" будет ", " не будет ", 1)
        elif lang == "RU" and " " in text:
            w1, w2 = text.split(" ", 1)
            t_neg = f"{w1} не {w2}"
        else:
            continue

        pairs.append({
            "pair_type": "negation_altered",
            "lang_a": lang,
            "lang_b": lang,
            "text_a": text,
            "text_b": t_neg,
            "gold_label": "different",
            "notes": "Negation toggled — factual contradiction"
        })
        neg_count += 1
        if neg_count >= 50:
            break

    # 6. Same topic, different claim (50 pairs)
    cats: Dict[int, List[Dict[str, Any]]] = {}
    for r in disinfo_recs:
        c = r["primary_label"]
        cats.setdefault(c, []).append(r)

    topic_diff = 0
    for c, c_recs in cats.items():
        if len(c_recs) >= 2:
            for i in range(0, min(len(c_recs) - 1, 10), 2):
                lang_a = "RO" if c_recs[i]["language"] == "ro" else "RU"
                lang_b = "RO" if c_recs[i+1]["language"] == "ro" else "RU"
                pairs.append({
                    "pair_type": "same_topic_different_claim",
                    "lang_a": lang_a,
                    "lang_b": lang_b,
                    "text_a": c_recs[i]["text"],
                    "text_b": c_recs[i+1]["text"],
                    "gold_label": "different",
                    "notes": f"Category {c} shared but distinct claims"
                })
                topic_diff += 1
                if topic_diff >= 50:
                    break

    # 7. Unrelated pairs (50 pairs)
    for d, b in zip(disinfo_recs[:50], benign_recs[:50]):
        lang_a = "RO" if d["language"] == "ro" else "RU"
        lang_b = "RO" if b["language"] == "ro" else "RU"
        pairs.append({
            "pair_type": "unrelated",
            "lang_a": lang_a,
            "lang_b": lang_b,
            "text_a": d["text"],
            "text_b": b["text"],
            "gold_label": "different",
            "notes": "Disinfo claim vs neutral benign report"
        })

    random.shuffle(pairs)
    return pairs


def build_clusters_eval(all_recs: List[Dict[str, Any]], target_count: int = 40) -> List[Dict[str, Any]]:
    """Build evaluation clusters representing realistic multi-channel cascades from real claims."""
    clusters = []
    disinfo_recs = [r for r in all_recs if r.get("is_disinformation") and len(r["text"]) > 40]

    for idx, r in enumerate(disinfo_recs[:target_count]):
        size = random.choice([2, 3, 4, 5])
        channels = [f"ch-feed-{i+1}" for i in range(size)]
        t_orig = r["text"]
        msgs = []
        for i in range(size):
            if i == 0:
                msg_text = t_orig
            elif i == 1:
                prefix = "⚡ URGENT: " if r["language"] == "ro" else "⚡ ВНИМАНИЕ: "
                msg_text = f"{prefix}{t_orig}"
            else:
                msg_text = f"{t_orig} (Canal #{i+1})"

            msgs.append({
                "id": f"msg-{idx:03d}-{i+1}",
                "channel_id": channels[i],
                "text": msg_text,
                "posted_at": f"2026-11-04T12:{i*3:02d}:00Z"
            })

        clusters.append({
            "cluster_id": f"eval-cl-{idx+1:03d}",
            "group_id": r.get("group_id", f"grp-{idx:03d}"),
            "size": size,
            "category": r.get("primary_label"),
            "messages": msgs,
        })

    return clusters


def main() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    train_recs = load_jsonl(PROCESSED_V1 / "train.jsonl")
    val_recs = load_jsonl(PROCESSED_V1 / "val.jsonl")
    test_recs = load_jsonl(PROCESSED_V1 / "test.jsonl")
    gold_recs = load_jsonl(PROCESSED_V1 / "gold.jsonl")
    all_recs = train_recs + val_recs + test_recs + gold_recs

    print(f"Loaded all authentic records: {len(all_recs)}")

    # 1. Hard negatives (>= 100 neutral items mentioning sensitive topics)
    hard_negatives = build_hard_negatives(all_recs, target_count=120)
    with open(EVAL_DIR / "hard_negatives.jsonl", "w", encoding="utf-8") as f:
        for r in hard_negatives:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[OK] Generated {len(hard_negatives)} benign hard negatives -> {EVAL_DIR / 'hard_negatives.jsonl'}")

    # 2. Pairs evaluation set (>= 300 balanced pairs)
    pairs = build_pairs_eval(all_recs)
    with open(EVAL_DIR / "pairs_eval.jsonl", "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"[OK] Generated {len(pairs)} balanced evaluation pairs -> {EVAL_DIR / 'pairs_eval.jsonl'}")

    # 3. Clusters evaluation set (>= 35 clusters)
    clusters = build_clusters_eval(all_recs, target_count=40)
    with open(EVAL_DIR / "clusters_eval.jsonl", "w", encoding="utf-8") as f:
        for cl in clusters:
            f.write(json.dumps(cl, ensure_ascii=False) + "\n")
    print(f"[OK] Generated {len(clusters)} evaluation clusters -> {EVAL_DIR / 'clusters_eval.jsonl'}")


if __name__ == "__main__":
    main()
