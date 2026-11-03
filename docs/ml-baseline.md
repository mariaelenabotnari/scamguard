# ML Pipeline Baseline Report

> Evaluation Date: November 2026  
> Model Version: Baseline (v1.0)  
> Harness: `ml/eval/run.py` on `pairs_eval.jsonl`, `clusters_eval.jsonl`, `narrative_eval.jsonl`, and planted simulation stream.

---

## 1. Summary Metrics Table

| Pipeline Component | Metric | Baseline Value | Observations & Notes |
|---|---|---|---|
| **Similarity Engine** | Precision (Overall) | **0.5385** | High false positive rate on texts with altered numbers, dates, or negations. |
| | Recall (Overall) | **0.7778** | Misses short paraphrased posts and nuanced rewrites. |
| | F1 Score (Overall) | **0.6364** | Baseline balance before character n-grams and verification step. |
| | RO-RO F1 | **0.5000** | Monolingual pairs suffer from detail-swapped false positives. |
| | RU-RU F1 | **0.5000** | Transliteration and punctuation stripping cause false collisions. |
| | RO-RU Cross-lingual F1 | **1.0000** | Concept lexicon matches seed cross-lingual claims. |
| **Clustering Engine** | B-cubed Precision | **0.1941** | Severe chaining ("snowball effect") from connected components. |
| | B-cubed Recall | **0.9265** | Groups everything into broad components. |
| | B-cubed F1 | **0.3210** | Low precision degrades overall clustering fidelity. |
| | Largest Cluster Size | **28** messages | Mega-cluster grouping distinct messages. |
| | Giant Clusters (>15) | **5** clusters | Unbounded diameter allows unrelated cascades to merge. |
| **Narrative Classifier** | Macro F1 | **0.4025** | Keyword-based prototype matcher struggles with low-resource classes. |
| | Unknown Rate | **0.0417** | 4.2% classified as unknown at 0.55 threshold. |
| | Expected Calibration Error | **0.1442** | Heuristic confidence estimation deviates ~14.4% from empirical accuracy. |
| **Scoring & Ranking** | Top-k Hit Rate | **0.0000** | Activity volume dominates over coordination delay and repetition. |
| | Rank Correlation | **-0.8609** | Background channels with high generic volume ranked above subtle coordinated groups. |
| **System Performance**| Throughput | **~25,800 msg/s** | Extremely fast heuristic operations on CPU. |

---

## 2. Target Improvements for v2

1. **Similarity v2**:
   - Character n-grams for short posts ($\le 12$ words).
   - LSH signature verification step with estimated Jaccard $\ge 0.70$ and 128 hashes.
   - Detail Guard to penalize changed numbers, dates, or negation flips.
   - Target: Boost similarity precision from `0.5385` to $\ge 0.85$, improving overall F1 to $\ge 0.80$.
2. **Clustering v2**:
   - Replace single-linkage transitive closure with average-linkage distance cut ($\le 0.25$, i.e. similarity $\ge 0.75$) and maximum diameter cap.
   - Prevent giant clusters (target: 0 giant clusters on simulation).
   - Target: Boost B-cubed F1 from `0.3210` to $\ge 0.75$.
3. **Text Representations v2**:
   - Separate into `text_hash` (strong), `text_model` (light), and `text_display` (raw).
   - Stop feeding transliterated text into semantic embeddings.

