# ScamGuard ML — Narrative Classifier Transformer Baseline Report

> **Branch**: `chore/ml-transformer-baseline`  
> **Evaluation Harness**: `ml/scripts/benchmark_comparison.py`  
> **Model Checkpoint**: `ml/models/narrative_classifier.joblib` (TF-IDF + Balanced Logistic Regression)  
> **Evaluation Date**: November 2026  
> **Anti-Leakage Verification**: `ml/tests/test_no_leakage.py` passed (0 group_id overlap, 0 exact text collisions, gold quarantined)

---

## 1. Executive Summary & Baseline Architecture

This document establishes the **frozen baseline** for the narrative classification engine of ScamGuard before evaluating multilingual transformer candidates.

### Baseline Specifications
- **Model Architecture**: `TfidfVectorizer(ngram_range=(1, 3), max_features=30000, sublinear_tf=True)` + `LogisticRegression(max_iter=1000, C=2.0, class_weight="balanced")`
- **Training Corpus**: `ml/data/processed/v1/train_augmented.jsonl` ($N=6,458$ items, balanced Telegram weak supervision)
- **Model Size on Disk**: **4.18 MB** (4,385,924 bytes)
- **Inference Throughput (CPU)**: **6,243 texts/sec**
- **Unified Interface**: Conforms to `NarrativeClassifierModel` (`predict_proba(texts: list[str]) -> np.ndarray` shape `[N, 13]`)

### Data & Caveats
> [!IMPORTANT]
> **Telegram Labels Caveat**: The 400 Telegram records (`telegram_labeled_400.jsonl`, split into `telegram_train.jsonl` and `telegram_test.jsonl`) were labeled by a **rule-based keyword heuristic script**, not by verified human annotators. These labels serve as weak supervision and preliminary evaluation, not as ground-truth truth. When human-verified labels are finalized, the evaluation suite will be rerun on that verified cohort.

> [!WARNING]
> **Majority Baseline Reality**: On `telegram_test.jsonl`, category 10 ("Other / not disinformation (Benign)") constitutes **61.3%** of the dataset. A degenerate model that always outputs "benign" achieves 61.3% accuracy without detecting a single disinformation narrative. Therefore, **Macro F1 with 95% bootstrap confidence intervals** is our primary evaluation criterion.

---

## 2. Headline Performance Summary

All confidence intervals are **95% Percentile Bootstrap Confidence Intervals** calculated over 1,000 resamples with fixed seed (`seed=42`).

| Evaluation Split | $N$ | Macro F1 (Present Classes) | Macro F1 (All 13 Classes) | Accuracy | Majority-Class Baseline | Unknown Rate ($\tau=0$) | Hard Negatives FPR |
|---|---|---|---|---|---|---|---|
| **Generalization Test Set (`test.jsonl`)** | 970 | **0.5245** [0.4771, 0.5660] | **0.4438** [0.4037, 0.4789] | **76.0%** | **40.8%** (Cat 10) | 0.0% | — |
| **Quarantined Moldovan Gold (`gold.jsonl`)** | 150 | **0.0916** [0.0591, 0.1132] | **0.0845** [0.0545, 0.1045] | **30.0%** | **26.7%** (Cat 10) | 0.0% | — |
| **Real Telegram Test Set (`telegram_test.jsonl`)** | 150 | **0.2629** [0.1890, 0.3163] | **0.1618** [0.1163, 0.1946] | **63.3%** | **61.3%** (Cat 10) | 0.0% | — |
| **Benign Hard Negatives (`hard_negatives.jsonl`)** | 120 | — | — | — | — | — | **0.0%** [0.0%, 0.0%] |

---

## 3. Detailed Split-by-Split Analysis

### 3.1 Generalization Test Set (`test.jsonl`)
* **Sample Size**: 970 items (multi-source: EUvsDisinfo, StopFals.md, MOROCO, Gazeta.ru, FAKEROM)
* **Accuracy**: 76.0% (vs. Majority Baseline: 40.8%)
* **Macro F1 (present 11 classes)**: 0.5245 [95% CI: 0.4771, 0.5660]
* **Macro F1 (all 13 classes)**: 0.4438 [95% CI: 0.4037, 0.4789]

#### Per-Class Performance
| ID | Category Name | Precision | Recall | F1 Score | Support |
|---|---|---|---|---|---|
| **1** | War in Ukraine & Russia justification | 0.6937 | 0.7938 | **0.7404** | 97 |
| **2** | Anti-EU / Europe falling apart | 0.6250 | 0.6024 | **0.6135** | 83 |
| **3** | Anti-NATO / anti-West | 0.5263 | 0.5556 | **0.5405** | 90 |
| **4** | Moldova govt & elections delegitimation | 0.3846 | 0.4688 | **0.4225** | 32 |
| **5** | Russophobia, language & identity | 0.6471 | 0.5570 | **0.5986** | 79 |
| **6** | Sanctions, energy & economy fear | 0.2500 | 0.1429 | **0.1818** | 7 |
| **7** | Transnistria / Gagauzia separatism | 0.0000 | 0.0000 | **0.0000** | 1 |
| **8** | Health, vaccines & conspiracy | 0.6593 | 0.7143 | **0.6857** | 84 |
| **9** | Traditional values & anti-LGBT | 0.5833 | 0.4667 | **0.5185** | 15 |
| **10** | Other / not disinformation (Benign) | 0.9925 | 1.0000 | **0.9962** | 396 |
| **11** | Financial panic & bank runs | 0.0000 | 0.0000 | **0.0000** | 0 |
| **12** | Forced mobilization & border militarization | 0.0000 | 0.0000 | **0.0000** | 0 |
| **13** | Other disinformation | 0.5211 | 0.4302 | **0.4713** | 86 |

#### Confusion Matrix (`test.jsonl`)
```text
True \ Pred |   1   2   3   4   5   6   7   8   9  10  11  12  13
-----------------------------------------------------------------
Cat 1 (War) |  77   3   2   5   7   0   0   0   0   0   0   0   3
Cat 2 (EU)  |   3  50  16   3   3   1   0   1   1   0   0   0   5
Cat 3 (NATO)|   4   5  50   5   2   0   0  12   2   1   0   0   9
Cat 4 (Gov) |   8   3   4  15   1   0   0   0   0   0   0   0   1
Cat 5 (Russ)|   6   6  10   0  44   0   0   5   0   2   0   0   6
Cat 6 (Econ)|   0   1   3   0   1   1   0   0   0   0   0   0   1
Cat 7 (Trans|   0   0   0   1   0   0   0   0   0   0   0   0   0
Cat 8 (Heal)|   2   3   6   1   1   0   0  60   2   0   0   0   9
Cat 9 (Trad)|   2   1   1   1   2   0   0   1   7   0   0   0   0
Cat 10(Ben) |   0   0   0   0   0   0   0   0   0 396   0   0   0
Cat 13(OthD)|   9   8   3   8   7   2   0  12   0   0   0   0  37
```

---

### 3.2 Quarantined Moldovan Gold Set (`gold.jsonl`)
* **Sample Size**: 150 items (strictly isolated from training; Romanian & Russian fact-check claims)
* **Accuracy**: 30.0% (vs. Majority Baseline: 26.7%)
* **Macro F1 (present 12 classes)**: **0.0916** [95% CI: 0.0591, 0.1132]
* **Macro F1 (all 13 classes)**: **0.0845** [95% CI: 0.0545, 0.1045]

#### Per-Class Performance
| ID | Category Name | Precision | Recall | F1 Score | Support |
|---|---|---|---|---|---|
| **1** | War in Ukraine & Russia justification | 0.0000 | 0.0000 | **0.0000** | 10 |
| **2** | Anti-EU / Europe falling apart | 0.0000 | 0.0000 | **0.0000** | 10 |
| **3** | Anti-NATO / anti-West | 0.0000 | 0.0000 | **0.0000** | 10 |
| **4** | Moldova govt & elections delegitimation | 0.0000 | 0.0000 | **0.0000** | 10 |
| **5** | Russophobia, language & identity | 0.0000 | 0.0000 | **0.0000** | 10 |
| **6** | Sanctions, energy & economy fear | 0.0000 | 0.0000 | **0.0000** | 10 |
| **7** | Transnistria / Gagauzia separatism | 1.0000 | 0.5000 | **0.6667** | 10 |
| **8** | Health, vaccines & conspiracy | 0.0000 | 0.0000 | **0.0000** | 10 |
| **9** | Traditional values & anti-LGBT | 0.0000 | 0.0000 | **0.0000** | 10 |
| **10** | Other / not disinformation (Benign) | 0.2759 | 1.0000 | **0.4324** | 40 |
| **11** | Financial panic & bank runs | 0.0000 | 0.0000 | **0.0000** | 10 |
| **12** | Forced mobilization & border militarization | 0.0000 | 0.0000 | **0.0000** | 10 |
| **13** | Other disinformation | 0.0000 | 0.0000 | **0.0000** | 0 |

#### Confusion Matrix (`gold.jsonl`)
```text
True \ Pred |   1   2   3   4   5   6   7   8   9  10  11  12  13
-----------------------------------------------------------------
Cat 1 (War) |   0   0   0   0   0   0   0   0   0  10   0   0   0
Cat 2 (EU)  |   0   0   0   0   0   0   0   0   0  10   0   0   0
Cat 3 (NATO)|   0   0   0   0   0   0   0   0   0  10   0   0   0
Cat 4 (Gov) |   0   0   0   0   0   0   0   0   0  10   0   0   0
Cat 5 (Russ)|   0   0   0   0   0   0   0   0   0  10   0   0   0
Cat 6 (Econ)|   0   0   0   0   0   0   0   0   0  10   0   0   0
Cat 7 (Trans|   0   0   0   0   0   0   5   0   0   5   0   0   0
Cat 8 (Heal)|   0   0   0   0   0   0   0   0   0  10   0   0   0
Cat 9 (Trad)|   0   0   0   0   0   0   0   0   0  10   0   0   0
Cat 10(Ben) |   0   0   0   0   0   0   0   0   0  40   0   0   0
Cat 11(Bank)|   0   0   0   0   0   0   0   0   0  10   0   0   0
Cat 12(Mobi)|   0   0   0   0   0   0   0   0   0  10   0   0   0
```
*Diagnosis*: Because n-gram features learned from international debunk corpora did not overlap with specific Moldovan political entities in the quarantined set, the linear model collapsed into predicting Category 10 for 145 out of 150 items. Only Category 7 ("Transnistria", "Tiraspol") retained high enough lexical salience to be recognized.

---

### 3.3 Real Telegram Test Set (`telegram_test.jsonl`)
* **Sample Size**: 150 items (authentic Telegram channel broadcasts)
* **Accuracy**: **63.3%** (vs. Majority Baseline: **61.3%**)
* **Macro F1 (present 8 classes)**: **0.2629** [95% CI: 0.1890, 0.3163]
* **Macro F1 (all 13 classes)**: **0.1618** [95% CI: 0.1163, 0.1946]

#### Per-Class Performance
| ID | Category Name | Precision | Recall | F1 Score | Support |
|---|---|---|---|---|---|
| **1** | War in Ukraine & Russia justification | 0.4667 | 0.3333 | **0.3889** | 21 |
| **2** | Anti-EU / Europe falling apart | 0.0000 | 0.0000 | **0.0000** | 4 |
| **3** | Anti-NATO / anti-West | 0.0000 | 0.0000 | **0.0000** | 4 |
| **4** | Moldova govt & elections delegitimation | 0.0000 | 0.0000 | **0.0000** | 2 |
| **5** | Russophobia, language & identity | 0.0000 | 0.0000 | **0.0000** | 0 |
| **6** | Sanctions, energy & economy fear | 0.4118 | 0.4118 | **0.4118** | 17 |
| **7** | Transnistria / Gagauzia separatism | 0.7500 | 0.4286 | **0.5455** | 7 |
| **8** | Health, vaccines & conspiracy | 0.0000 | 0.0000 | **0.0000** | 0 |
| **9** | Traditional values & anti-LGBT | 0.0000 | 0.0000 | **0.0000** | 0 |
| **10** | Other / not disinformation (Benign) | 0.6842 | 0.8478 | **0.7573** | 92 |
| **11** | Financial panic & bank runs | 0.0000 | 0.0000 | **0.0000** | 0 |
| **12** | Forced mobilization & border militarization | 0.0000 | 0.0000 | **0.0000** | 0 |
| **13** | Other disinformation | 0.0000 | 0.0000 | **0.0000** | 3 |

#### Confusion Matrix (`telegram_test.jsonl`)
```text
True \ Pred |   1   2   3   4   5   6   7   8   9  10  11  12  13
-----------------------------------------------------------------
Cat 1 (War) |   7   0   0   0   0   0   0   0   0  14   0   0   0
Cat 2 (EU)  |   1   0   0   0   0   0   0   0   0   3   0   0   0
Cat 3 (NATO)|   1   0   0   0   0   2   0   0   0   1   0   0   0
Cat 4 (Gov) |   0   0   0   0   0   0   0   0   0   2   0   0   0
Cat 6 (Econ)|   0   0   0   0   0   7   0   0   0  10   0   0   0
Cat 7 (Trans|   0   0   0   0   0   0   3   0   0   4   0   0   0
Cat 10(Ben) |   6   0   0   0   0   8   0   0   0  78   0   0   0
Cat 13(OthD)|   0   0   0   0   0   0   1   0   0   2   0   0   0
```

---

## 4. Confidence-Threshold Calibration Analysis ($\tau = 0.38$)

When evaluated with calibrated confidence thresholding ($\tau = 0.38$), predictions whose maximum class probability is $< 0.38$ are marked as `unknown` ($0$):

| Metric | `test.jsonl` ($\tau=0.38$) | `gold.jsonl` ($\tau=0.38$) | `telegram_test.jsonl` ($\tau=0.38$) |
|---|---|---|---|
| **Macro F1 (Present Classes)** | 0.4542 [0.4171, 0.4888] | 0.0952 [0.0639, 0.1165] | 0.2350 [0.1566, 0.2926] |
| **Accuracy** | 63.6% | 26.7% | 48.7% |
| **Majority Baseline** | 40.8% | 26.7% | 61.3% |
| **Unknown Rate** | **27.4%** | **25.3%** | **29.3%** |

*Key finding*: At $\tau = 0.38$, low-confidence noisy predictions are discarded into `unknown`, lowering the raw accuracy on Telegram (from 63.3% to 48.7%) while maintaining precision on high-confidence assertions.

---

## 5. End-to-End Hybrid Pipeline (`NarrativeClassifierService`) Performance

In the production ScamGuard architecture, the ML classifier does not operate in isolation; it functions as **Signal 4 (ML Learned Evidence)** inside `NarrativeClassifierService`, where it is combined with keyword evidence (Signal 1), prototype cosine similarity (Signal 2), debunk retrieval (Signal 3), and multi-signal gating.

| Pipeline Configuration | `test.jsonl` Macro F1 | `gold.jsonl` Macro F1 | `telegram_test.jsonl` Macro F1 | Hard Negatives FPR |
|---|---|---|---|---|
| **Raw ML Classifier ($\tau=0.0$)** | 0.5245 | 0.0916 | 0.2629 | **0.0%** (0/120) |
| **Raw ML Classifier ($\tau=0.38$)** | 0.4542 | 0.0952 | 0.2350 | **0.0%** (0/120) |
| **Hybrid Pipeline ($\tau=0.38$)** | 0.3056 | **0.4179** | 0.2363 | **15.8%** (19/120) |
| **Hybrid Pipeline ($\tau=0.55$, default)**| 0.1777 | 0.3471 | 0.2011 | **7.5%** (9/120) |

*Insight*: The hybrid service boosts performance on the quarantined Moldovan Gold set from 0.0916 to **0.4179** via debunk retrieval and concept vectors. However, on raw conversational Telegram posts, both the raw TF-IDF model (0.2629) and the hybrid pipeline (0.2363) struggle to separate subtle propaganda from benign discourse.

---

## 6. Target Benchmarks for Transformer Candidates (`feat/ml-transformer-train`)

Any candidate transformer model must outperform the baseline on:
1. **Real Telegram Macro F1**: Must strictly exceed **0.2629** (present classes) / **0.1618** (all 13 classes).
2. **Accuracy above Majority Baseline**: Must clearly outperform the **61.3%** majority baseline on `telegram_test.jsonl`.
3. **Quarantined Gold Macro F1**: Must exceed **0.0916** standalone.
4. **Hard Negatives FPR**: False positive rate on 120 neutral news articles must remain $< 10.0\%$.
5. **CPU Latency**: Must maintain at least $\ge 15$ texts/sec on CPU for near-real-time stream processing.
