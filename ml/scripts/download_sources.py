"""
Download and extract candidate raw datasets for narrative classification.
Vetted sources:
1. EUvsDisinfo (Kaggle: imuhammad/euvsdisinfo-disinformation-database & Zenodo: 10514307)
2. MOROCO (GitHub: butnaruandrei/MOROCO - Moldavian & Romanian Dialectal Corpus)
3. FAKEROM (Hugging Face: mihalca/Fakerom_updated_original & mateiaass/FakeRom)
4. Russian Benign News (Hugging Face: IlyaGusev/gazeta)
"""

import json
import os
import sys
from pathlib import Path
import requests
import pandas as pd

RAW_DIR = Path("ml/data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest_path: Path, chunk_size: int = 65536) -> bool:
    if dest_path.exists() and dest_path.stat().st_size > 0:
        print(f"[SKIP] Already exists: {dest_path.name} ({dest_path.stat().st_size} bytes)")
        return True
    
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[*] Downloading {url} -> {dest_path.name} ...")
    try:
        headers = {"User-Agent": "ScamGuard-Research/1.0"}
        with requests.get(url, stream=True, headers=headers, timeout=60) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
        print(f"[OK] Downloaded {dest_path.name} ({dest_path.stat().st_size} bytes)")
        return True
    except Exception as e:
        print(f"[ERR] Failed to download {url}: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False


def fetch_euvsdisinfo():
    """Download EUvsDisinfo dataset via Kaggle and Zenodo."""
    print("\n--- 1. Fetching EUvsDisinfo ---")
    target_dir = RAW_DIR / "euvsdisinfo_db"
    target_dir.mkdir(parents=True, exist_ok=True)
    csv_file = target_dir / "euvsdisinfo_v1_2.csv"
    
    if csv_file.exists() and csv_file.stat().st_size > 0:
        print(f"[SKIP] EUvsDisinfo already present ({csv_file.stat().st_size} bytes)")
        return True

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        print("[*] Downloading imuhammad/euvsdisinfo-disinformation-database from Kaggle...")
        api.dataset_download_files("imuhammad/euvsdisinfo-disinformation-database", path=str(target_dir), unzip=True)
        print(f"[OK] EUvsDisinfo downloaded successfully to {target_dir}")
        return True
    except Exception as e:
        print(f"[ERR] Kaggle download failed: {e}")
        return False


def fetch_moroco():
    """Download MOROCO directly from GitHub raw files."""
    print("\n--- 2. Fetching MOROCO (Moldavian & Romanian Dialectal Corpus) ---")
    target_dir = RAW_DIR / "moroco"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    base_url = "https://raw.githubusercontent.com/butnaruandrei/MOROCO/master/MOROCO/preprocessed/all/"
    files = [
        "train_samples.txt",
        "train_category_labels.txt",
        "train_dialect_labels.txt",
        "validation_samples.txt",
        "validation_category_labels.txt",
        "validation_dialect_labels.txt",
        "test_samples.txt",
        "test_category_labels.txt",
        "test_dialect_labels.txt",
    ]
    
    all_ok = True
    for fname in files:
        url = base_url + fname
        dest = target_dir / fname
        ok = download_file(url, dest)
        if not ok:
            all_ok = False
            
    return all_ok


def fetch_fakerom():
    """Download Romanian fake news corpora from Hugging Face."""
    print("\n--- 3. Fetching FAKEROM Romanian Corpora ---")
    target_dir = RAW_DIR / "fakerom"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    out_file = target_dir / "fakerom_combined.jsonl"
    if out_file.exists() and out_file.stat().st_size > 0:
        print(f"[SKIP] FAKEROM combined file already exists ({out_file.stat().st_size} bytes)")
        return True

    try:
        from datasets import load_dataset
        print("[*] Loading mihalca/Fakerom_updated_original from Hugging Face...")
        ds1 = load_dataset("mihalca/Fakerom_updated_original")
        
        count = 0
        with open(out_file, "w", encoding="utf-8") as f:
            for row in ds1["train"]:
                record = {
                    "text": row.get("text") or row.get("content") or "",
                    "title": row.get("title") or "",
                    "label": row.get("label"),
                    "source": "mihalca/Fakerom_updated_original",
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
                
        print(f"[OK] Saved {count} rows to {out_file.name}")
        return True
    except Exception as e:
        print(f"[ERR] Failed to load FAKEROM: {e}")
        return False


def fetch_gazeta_russian_benign(sample_size: int = 1500):
    """Download Russian benign news samples from Hugging Face IlyaGusev/gazeta."""
    print("\n--- 4. Fetching Russian Benign News (IlyaGusev/gazeta) ---")
    target_dir = RAW_DIR / "gazeta_ru"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    out_file = target_dir / "gazeta_sample.jsonl"
    if out_file.exists() and out_file.stat().st_size > 0:
        print(f"[SKIP] Gazeta sample already exists ({out_file.stat().st_size} bytes)")
        return True
        
    try:
        from datasets import load_dataset
        print("[*] Loading IlyaGusev/gazeta from Hugging Face...")
        ds = load_dataset("IlyaGusev/gazeta", split=f"train[:{sample_size}]")
        
        count = 0
        with open(out_file, "w", encoding="utf-8") as f:
            for row in ds:
                record = {
                    "text": row.get("text") or "",
                    "title": row.get("title") or "",
                    "summary": row.get("summary") or "",
                    "date": row.get("date") or "",
                    "url": row.get("url") or "",
                    "source": "IlyaGusev/gazeta",
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
                
        print(f"[OK] Saved {count} Russian benign news samples to {out_file.name}")
        return True
    except Exception as e:
        print(f"[ERR] Failed to load IlyaGusev/gazeta: {e}")
        return False


if __name__ == "__main__":
    print("=== Downloading and Ingesting Raw Datasets for Narrative Classifier ===")
    r_euv = fetch_euvsdisinfo()
    r_moroco = fetch_moroco()
    r_fakerom = fetch_fakerom()
    r_gazeta = fetch_gazeta_russian_benign()
    
    print("\n=== Download Summary ===")
    print(f"EUvsDisinfo:    {'SUCCESS' if r_euv else 'FAILED'}")
    print(f"MOROCO:         {'SUCCESS' if r_moroco else 'FAILED'}")
    print(f"FAKEROM:        {'SUCCESS' if r_fakerom else 'FAILED'}")
    print(f"Gazeta (RU):    {'SUCCESS' if r_gazeta else 'FAILED'}")
