"""Audit seed dataset for translation leakage, sizes, and URL verification."""

import json
import urllib.error
import urllib.request
from pathlib import Path

SEED_PATH = Path("ml/data/seed/moldova_debunk_claims.jsonl")
PROCESSED_DIR = Path("ml/data/processed")


def main() -> None:
    lines = [line.strip() for line in SEED_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [json.loads(line) for line in lines]

    print(f"Total rows in seed file: {len(rows)}")

    # Check splits
    train_ids = set()
    val_ids = set()
    test_ids = set()

    if (PROCESSED_DIR / "train.jsonl").exists():
        train_ids = {json.loads(l)["id"] for l in (PROCESSED_DIR / "train.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    if (PROCESSED_DIR / "val.jsonl").exists():
        val_ids = {json.loads(l)["id"] for l in (PROCESSED_DIR / "val.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    if (PROCESSED_DIR / "test.jsonl").exists():
        test_ids = {json.loads(l)["id"] for l in (PROCESSED_DIR / "test.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}

    print(f"Split counts: train={len(train_ids)}, val={len(val_ids)}, test={len(test_ids)}")

    results = []
    for r in rows:
        cid = r["id"]
        url = r.get("debunk_url", "")
        status = "N/A"
        if url:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    status = f"HTTP {resp.status}"
            except urllib.error.HTTPError as e:
                status = f"HTTP {e.code}"
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                status = f"ERR: {type(e).__name__}"

        split = "train" if cid in train_ids else "val" if cid in val_ids else "test" if cid in test_ids else "unassigned"
        results.append({
            "id": cid,
            "split": split,
            "lang": r["language"],
            "cat_id": r["category_id"],
            "cat_name": r["category_name"],
            "is_disinfo": r["is_disinformation"],
            "source": r["source"],
            "debunk_url": url,
            "url_status": status,
            "text": r["text"],
            "char_len": len(r["text"]),
        })

    with open("ml/data/seed/audit_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    for res in results:
        print(f"{res['id']} | {res['split']} | {res['lang']} | Cat {res['cat_id']} | Disinfo: {res['is_disinfo']} | {res['source']} | URL: {res['url_status']} | Len: {res['char_len']}")


if __name__ == "__main__":
    main()
