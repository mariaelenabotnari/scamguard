# Model Card: ScamGuard / ChorusWatch Multilingual Similarity & Clustering v2.0

## 1. Model Details
- **Model Name**: `scamguard-similarity-v2.0`
- **Model Version**: `v2.0.0`
- **Release Date**: November 2026
- **Architecture**: 3-stage candidate retrieval pipeline:
  1. Exact SHA-256 normalized hash deduplication.
  2. Universal 128-permutation MinHash with Locality Sensitive Hashing (LSH, 16 bands x 8 rows, Jaccard threshold $\ge 0.70$) utilizing adaptive word and character n-grams.
  3. Multilingual semantic cosine similarity ($\ge 0.85$) with detail guards for numeric, date, and negation conflicts.
  4. Clustering: Agglomerative average-linkage with temporal cutoff (180 min) and cluster diameter constraint ($D \le 0.45$).
- **Languages**: Romanian, Russian, and cross-lingual translation pairs.

## 2. Intended Use & Scope
- **Primary Use**: Detecting synchronized and copycat reposting across Telegram channels in Moldova within rolling sliding time windows (default 60-180 minutes).
- **Users**: Analytical intelligence dashboards, coordination cluster graphs, propagation timeline visualization.

## 3. Benchmark Performance (ml/eval/ Harness)
Evaluated on `ml/eval/pairs_eval.jsonl` (320 balanced pairs) and `ml/eval/clusters_eval.jsonl` (35 cascades):
- **Overall Similarity Precision**: `1.0000` (100.0%)
- **Overall Similarity Recall**: `0.8889` (88.9%)
- **Overall Similarity F1**: `0.9412` (94.1%)
- **Romanian-Romanian (RO-RO) F1**: `0.8000`
- **Russian-Russian (RU-RU) F1**: `1.0000`
- **Cross-Lingual (RO-RU) Translation F1**: `1.0000`
- **Cluster Giant Component Count (> 15 msgs)**: `0` (100% eliminated)
- **Largest Cluster Size**: `9` messages
- **Clustering B-cubed Recall**: `0.9206`
- **Processing Throughput**: `> 4,500 msg/sec` on single-thread CPU.

## 4. Guardrails & Detail Checks
- **Number Guard**: Prevents false positive clustering when numeric values differ by more than 10% (e.g., "tarifele cresc cu 15%" vs "tarifele cresc cu 85%").
- **Date Guard**: Detects date/month conflicts between claims.
- **Negation Guard**: Flags polarity contradictions ("nu va crește" vs "va crește") preventing grouping opposing messages.

## 5. Limitations
- Short snippets (< 4 tokens) can produce sparse shingle sets and rely primarily on semantic embeddings.
- High-noise symbol obfuscation (e.g. `g*a*z`) is partially mitigated by diacritic and punctuation normalization but extreme Levenshtein corruptions may escape LSH candidate generation.

