# Scamguard / ChorusWatch ML & NLP Workspace

This directory holds offline evaluation harnesses, training data sources, label mapping, and model retraining workflows for Telegram coordination and disinformation detection in Moldova (Romanian and Russian).

## Structure

- `data/`:
  - `SOURCES.md`: License, source provenance, and privacy notes for all datasets.
  - `moldova_debunk_claims.jsonl`: Curated Moldovan debunk database (StopFals.md, EUvsDisinfo).
- `eval/`:
  - `pairs_eval.jsonl`: 320 balanced evaluation pairs for similarity benchmarks.
  - `clusters_eval.jsonl`: 35 realistic multi-channel cascades in Moldova.
  - `narrative_eval.jsonl`: 360 balanced bilingual Telegram posts across all 12 categories.
  - `simulated_stream.jsonl` & `simulated_campaigns.json`: Planted campaign simulation stream.
  - `run.py`: Standard evaluation harness runner.
- `scripts/`:
  - `label_map.yaml`: The official 12-category taxonomy with prototype claims, keywords, and sub-narratives.
- `notebooks/`: EDA and error analysis notebooks.

> **Rule**: The backend (`backend/app/`) only loads trained artifacts and evaluation models for inference. Training code never runs inside the live FastAPI server.

---

## Retraining & Deployment Checklist

When retraining models or integrating fresh fact-check debunks, follow these strict gates before updating backend models:

### 1. Ingest New Ground Truth Debunks
- Export verified debunk claims from StopFals.md, EUvsDisinfo, and analyst feedback from the `classification_feedback` database table.
- Verify license and attribution in `ml/data/SOURCES.md`.
- Append valid entries to `ml/data/moldova_debunk_claims.jsonl`.

### 2. Leak-Free Dataset Splitting
- Split datasets by **source**, **date**, and **near-duplicate cluster hash** (never random train/test split). Many debunk datasets repeat the exact same claim text under different article IDs.

### 3. Run Offline Evaluation
Run the standardized evaluation harness:
```bash
python ml/eval/run.py
```

### 4. Deployment Quality Gates
Before any model artifact or parameter update is committed and deployed to the backend, verify that all quality gates pass:
| Metric | Minimum Gate Threshold | Current v2.0 Benchmark |
| :--- | :--- | :--- |
| **Similarity Overall Precision** | $\ge 0.90$ | **1.0000** |
| **Similarity Overall Recall** | $\ge 0.85$ | **0.8889** |
| **Similarity Overall F1** | $\ge 0.88$ | **0.9412** |
| **Giant Clusters (> 15 messages)** | $= 0$ (no chaining) | **0** |
| **Narrative Classifier Macro F1** | $\ge 0.80$ | **0.8444** |
| **Expected Calibration Error (ECE)**| $\le 0.10$ | **0.0818** |
| **Scoring Top-5 Hit Rate** | $\ge 0.80$ | **1.0000** |
| **Scoring Rank Correlation** | $\ge +0.70$ | **+0.7748** |
| **CPU Processing Throughput** | $\ge 2,500$ msg/sec | **> 4,500 msg/sec** |

### 5. Versioning & Model Cards
- Increment parameter version tag (e.g. `v2.0.0-scoring`, `scamguard-xlmr-multilingual-v2.0`).
- Update the corresponding model card in `docs/model-cards/`.
- Record validation results in `docs/ml-report.md`.


