# ScamGuard Machine Learning & Data Science Code Audit

This audit examines the data science and ML components in `backend/app/services/` and `ml/`, documenting code findings, verified lines, and required improvements.

---

## Audit Findings Matrix

| Finding # | Component & File | Code Location | Verdict | Analysis & Verification |
|---|---|---|---|---|
| **1. Single-Keyword False Positives** | `narrative_classifier_service.py` | Lines 388, 416–418 | **CONFIRMED** | `score += 0.55 + min(0.35, (hits - 1) * 0.12)` guarantees that a single keyword match (e.g. *bruxelles*, *fraudă*, *mobilizare*) produces a score $\ge 0.55$, which equals `confidence_threshold = 0.55`. Normal news mentioning official government agencies or European events gets labeled as disinformation. |
| **2. Misleading "Fake News Score"** | `narrative_classifier_service.py` | Lines 470–474 | **CONFIRMED** | `fake_score = round(conf if is_disinfo else 0.05, 4)` and DTO attribute `fakeNewsScore`. Assigns arbitrary `0.05` to benign news and renames category match confidence to "fake score", giving a false illusion of fact-checking certainty. |
| **3. Hand-Crafted Lexicon Vectors** | `similarity_service.py` | Lines 18–169, 188–200 | **CONFIRMED** | `_CONCEPT_GROUPS` consists of 16 hard-coded tuples of stems (`tarif`, `gaz`, `alegeri`, etc.) projected into a 48-dimensional vector. Fails on synonyms, modern slang, morphological variations, or novel geopolitical topics not present in the static list. |
| **4. Lack of Machine Learning from Data** | `narrative_classifier_service.py` | Lines 54–301 | **CONFIRMED** | The classifier solely evaluates keyword hits and static prototype claims. It did not train statistical or neural weights on verified datasets. |
| **5. Unvalidated Channel Risk Formula** | `scoring_service.py` | Lines 58–62, 80–83 | **CONFIRMED** | Linear combination `0.35*cp + 0.30*cd + 0.20*cm + 0.15*nw` and static risk thresholds (70/40) mix coordination behavior with narrative content. Lacks empirical calibration against coincidence baselines and breaking news bursts. |
| **6. Chaining Risk in Clustering** | `clustering_service.py` | Lines 104–109 | **CONFIRMED** | Connected components graph clustering without community diameter enforcement allows transitively linked messages (A $\sim$ B, B $\sim$ C, but A $\not\sim$ C) to form large diffuse clusters. |

---

## Action Plan
1. **`feat/ml-eval-harness`**: Construct a comprehensive evaluation harness in `ml/eval/` with balanced pair sets, hard negative sets, campaign simulator, and unified benchmark reporting (`run.py`).
2. **`fix/ml-classifier-false-positives`**: Remove fixed `0.55` base; require multi-signal evidence (keywords + prototype similarity + debunk match) and topic-vs-claim gating.
3. **`fix/ml-remove-fake-score`**: Rename `fakeNewsScore` $\to$ `narrative_match`, remove arbitrary `0.05`, and update APIs/DTOs.
4. **`feat/ml-real-embeddings`**: Integrate real multilingual sentence embeddings (`paraphrase-multilingual-MiniLM-L12-v2` / LaBSE / e5), keeping `baseline_lexicon` for comparison.
5. **`feat/ml-trained-classifier`**: Train calibrated classifier on `ml/data/processed/v1/` (`train.jsonl`, `val.jsonl`, `test.jsonl`, `gold.jsonl`).
6. **`feat/ml-scoring-validation`**: Separate coordination score and narrative severity flag into distinct visible axes; add minimum evidence guard and coincidence baseline.
7. **`fix/ml-clustering-checks`**: Enforce cluster diameter constraints and verify LSH + Jaccard recall.
