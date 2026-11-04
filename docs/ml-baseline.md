# ScamGuard ML & NLP Pipeline — Baseline Evaluation Report

> **Evaluation Benchmark Version**: `v1.0.0-baseline`  
> **Evaluation Datasets**: Authentic multi-source corpora (`ml/data/processed/v1/`), 317 evaluation pairs, 40 multi-channel cascades, 120 benign hard negatives.

---

## 1. Cross-Channel Similarity Engine

| Metric | Score | Target | Notes |
|---|---|---|---|
| **Overall Precision** | **0.9730** | $\ge 0.90$ | Exact hash + Adaptive MinHash/LSH verification |
| **Overall Recall** | **0.9391** | $\ge 0.85$ | Multi-lingual near-duplicate discovery |
| **Overall F1** | **0.9558** | $\ge 0.85$ | Balanced pairwise metric |
| **RO-RO F1** | **0.9919** | $\ge 0.85$ | Romanian monolingual pairs |
| **RU-RU F1** | **0.9873** | $\ge 0.85$ | Russian monolingual pairs |
| **RO-RU Cross-Lingual F1** | **0.6667** | $\ge 0.80$ | Semantic cross-lingual translation pairs |
| **Detail Guard Accuracy** | **1.0000** | $\ge 0.90$ | Discriminates changed numbers/dates and negation flips |

---

## 2. Cascade Clustering & Coordination Detection

| Metric | Score | Target | Notes |
|---|---|---|---|
| **B-cubed Precision** | **1.0000** | $\ge 0.70$ | Measures cluster purity |
| **B-cubed Recall** | **0.6788** | $\ge 0.80$ | Measures cascade completeness |
| **B-cubed F1** | **0.8087** | $\ge 0.75$ | Harmonized cascade grouping metric |
| **Largest Cluster Size** | **3** | $\le 15$ | Bounded maximum cascade size |
| **Giant Clusters Count** | **0** | 0 | Prevents uncontrolled component chaining |

---

## 3. Narrative Classifier Evaluation (Reported Separately)

| Evaluation Partition | Macro F1 | Unknown Rate | Expected Calibration Error (ECE) | Notes |
|---|---|---|---|---|
| **Held-Out Test Set (`v1`)** | **0.1832** | **0.5402** | **0.2797** | 970 unseen multi-source items |
| **Moldovan Gold Test Set** | **0.5566** | **0.2000** | — | 150 quarantined Moldovan evaluation items |

### Benign Hard Negatives Performance
* **False Positive Rate (FPR)**: **91.7%** (0.9167)
* *Finding*: The rule-based keyword bonus (+0.55) erroneously triggers disinformation classifications on neutral news mentioning words like *alegeri*, *gaz*, or *bruxelles*.

---

## 4. Scoring, Coordination Alerts & Latency

| Metric | Score | Operational SLA |
|---|---|---|
| **Planted Campaign Detection (Top-k Hit Rate)** | **85.0%** | $\ge 80.0\%$ |
| **Scoring Rank Correlation** | **0.7200** | $\ge 0.60$ |
| **Processing Throughput** | **2,240.0 msg/sec** | $\ge 1,000$ msg/sec |
