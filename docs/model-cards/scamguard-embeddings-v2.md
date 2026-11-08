# Model Card: ScamGuard Multilingual Similarity & Cascade Clustering v2.1

## 1. Model Details
- **Component Name**: `scamguard-similarity-v2.1` (`SimilarityService` + `ClusteringService`)
- **Version**: `v2.1.0` (Round 2 Upgrade)
- **Architecture**: 3-stage candidate retrieval & verification pipeline:
  1. **Stage 1 — Exact SHA-256 Normalized Hash**: $O(1)$ lookup for verbatim copies after NFKC, URL/handle stripping, and Romanian diacritic normalization.
  2. **Stage 2 — Verified Adaptive MinHash + LSH**: 128 universal hash permutations across 32 LSH bands using adaptive character 4/5-grams (short posts) and word 1–3-grams (longer posts), requiring both band collision and verified shingle Jaccard $\ge 0.65$.
  3. **Stage 3 — Dense Multilingual Embeddings (Default) with Lexicon Fallback**:
     - **Default (`SCAMGUARD_USE_DENSE_SIMILARITY_EMBEDDER=true`)**: `SentenceTransformerEmbedder` (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384-dim L2-normalized vectors, Apache-2.0 licence) with cross-lingual `RO-RU` calibration and process-level model/vector caching.
     - **Fallback (`SCAMGUARD_USE_DENSE_SIMILARITY_EMBEDDER=false`)**: `DeterministicMultilingualEmbedder` (48-dim concept lexicon + MD5 prefix hashing).
  4. **Adversarial Detail Guard (`check_detail_conflict`)**: Vetoes similarity edges when high-overlap texts ($J \ge 0.35$) contain opposing negation tokens (`nu`, `fără`, `не`, `нет`, `без`) or divergent numerical quantities/percentages.
  5. **Cascade Clustering**: Average-linkage agglomerative clustering with temporal window cutoff (180 min) and minimum pairwise diameter bound ($\ge 0.50$).

## 2. Benchmark Performance (`ml/eval/pairs_eval.jsonl`, $N = 317$ Pairs & `ml/eval/clusters_eval.jsonl`, $N = 35$ Cascades)

| Embedder Configuration | Overall Precision | Overall Recall | Overall F1 | `RO-RO` F1 ($N=129$) | `RU-RU` F1 ($N=122$) | `RO-RU` F1 ($N=66$) | Detail Guard Acc ($N=100$) | `clusters_eval` B-Cubed F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`SentenceTransformerEmbedder` (MiniLM Default, v2.1 `evaluate_similarity`)** | **0.9576** | **0.9826** | **0.9700** | 0.9760 | **1.0000** | **0.8667** | **0.9900** | **0.7943** |
| **`DeterministicMultilingualEmbedder` (Lexicon Fallback, v2.1 + Detail Guard Fix)** | **0.9643** | 0.9391 | 0.9515 | **0.9839** | 0.9873 | 0.6667 | **0.9900** | **0.8087** |
| `DeterministicMultilingualEmbedder` (Legacy v2.0, Before Detail Guard Fix) | 0.5775 | 0.9391 | 0.7152 | 0.8905 | 0.5532 | 0.6667 | 0.2100 | 0.8087 |

## 3. Limitations
- Cross-lingual `RO-RU` matching on heavily paraphrased idioms without shared named entities or numbers remains harder than monolingual `RO-RO` / `RU-RU` matching (`RO-RU` F1 `0.8667` vs `RU-RU` F1 `1.0000`).
- First-call initialization loads `paraphrase-multilingual-MiniLM-L12-v2` weights (~0.15s from local cache); subsequent calls share the in-memory singleton model and vector cache.
