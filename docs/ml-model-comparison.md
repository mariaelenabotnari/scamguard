# ScamGuard Narrative Classifier: Model Comparison & Evaluation Report

**Document Version:** 1.0.0  
**Date:** 2026-11-07  
**Branch:** `feat/ml-transformer`  
**Evaluation Scope:** Strict zero-leakage comparison across Generalization Test (`test.jsonl`), Quarantined Moldovan Gold Set (`gold.jsonl`), Real Telegram Broadcasts (`telegram_test.jsonl`), and Neutral News Hard Negatives (`hard_negatives.jsonl`).

---

## 1. Executive Summary

This report evaluates whether fine-tuned multilingual transformer architectures or frozen sentence encoders outperform the baseline **TF-IDF + Logistic Regression** narrative classifier (`ml/models/narrative_classifier.joblib`) deployed in ScamGuard.

All evaluations are conducted under identical zero-leakage partitions (`ml/tests/test_no_leakage.py`), reporting:
- 95% percentile bootstrap confidence intervals (1,000 resamples) for every F1 metric.
- The majority-class baseline alongside every accuracy score.
- False positive rates on 120 verified benign neutral news articles (`hard_negatives.jsonl`).
- Performance under both **Standalone Classification** and the **ScamGuard Multi-Signal Assertion Gate** (`NarrativeClassifierService`).

### Crucial Data Quality Notice
> [!WARNING]
> **Telegram Weak Supervision Notice:** The 400 authentic Moldovan Telegram messages were labeled using a rule-based keyword heuristic script (`label_telegram_messages.py`), **not human expert annotators**. The test set of 150 Telegram posts (`telegram_test.jsonl`) contains natural label noise from keyword false alarms (e.g. news mentioning gas prices labeled as economic disinformation). It serves as a real-world robustness check rather than immutable ground truth.

---

## 2. Comparative Benchmark Table

The table below summarizes performance across all candidate architectures evaluated on the same hardware (8-core CPU) and splits.

| Metric / Dimension | Baseline: TF-IDF + Logistic Regression | Candidate 1: Frozen MiniLM + Logistic Regression | Candidate 2: Fine-Tuned MiniLM Transformer |
|:---|:---:|:---:|:---:|
| **Architecture** | Word + Char TF-IDF + L2 LogisticRegression | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` + LogisticRegression | Fine-Tuned `MiniLM-L12-v2` (top 4 layers + CE loss) |
| **Model Disk Size** | **4.18 MB** | 0.04 MB (head) + 470 MB encoder | 448.86 MB |
| **CPU Throughput** | **6,243 texts/sec** | 23.9 texts/sec | 16.3 texts/sec |
| **Hard Negatives FPR (Standalone)** | **0.0%** [0.0%, 0.0%] | 55.8% [47.5%, 65.0%] | 10.8% [5.0%, 16.7%] |
| **Hard Negatives FPR (Hybrid Pipeline $\tau=0.38$)** | **15.8%** | 40.8% | 28.3% |
| **Generalization Test (`test.jsonl`, N=970)** | | | |
| - Macro F1 (all 13 categories) | **0.4438** [0.4132, 0.4727] | 0.3858 [0.3549, 0.4129] | 0.4304 [0.4018, 0.4571] |
| - Macro F1 (present 11 categories) | **0.5245** [0.4883, 0.5587] | 0.4560 [0.4195, 0.4879] | 0.5086 [0.4748, 0.5402] |
| - Accuracy | **76.0%** | 63.5% | 75.9% |
| - Majority Baseline Accuracy | 40.8% (Cat 10: Benign) | 40.8% | 40.8% |
| - Unknown Rate ($\tau=0.0$) | 0.0% | 0.0% | 0.0% |
| **Moldovan Gold Set (`gold.jsonl`, N=150)** | | | |
| - Macro F1 (all 13 categories) | 0.0845 [0.0352, 0.1437] | **0.5360** [0.4588, 0.5902] | 0.2551 [0.2112, 0.2889] |
| - Macro F1 (present 12 categories) | 0.0916 [0.0381, 0.1557] | **0.5806** [0.4970, 0.6394] | 0.2764 [0.2288, 0.3129] |
| - Accuracy | 30.0% | **63.3%** | 42.0% |
| - Majority Baseline Accuracy | 26.7% (Cat 10: Benign) | 26.7% | 26.7% |
| **Real Telegram Test (`telegram_test.jsonl`, N=150)** | | | |
| - Standalone Macro F1 (present 8) | 0.2629 [0.1691, 0.3541] | **0.2696** [0.1907, 0.3455] | 0.2272 [0.1427, 0.3085] |
| - Standalone Accuracy | **63.3%** | 40.0% | 60.0% |
| - Majority Baseline Accuracy | 61.3% (Cat 10: Benign) | 61.3% | 61.3% |
| - **Hybrid Pipeline Macro F1 ($\tau=0.38$)** | **0.4429** [0.3439, 0.5193] | 0.3993 [0.3045, 0.4773] | 0.3755 [0.2759, 0.4567] |
| - **Hybrid Pipeline Accuracy ($\tau=0.38$)** | **67.3%** | 61.3% | 61.3% |

---

## 3. Per-Class F1 Breakdown (Standalone Models)

### Generalization Test Set (`test.jsonl`)
| ID | Taxonomy Category Name | Baseline TF-IDF F1 | Frozen MiniLM F1 | Fine-Tuned MiniLM F1 | Support |
|:---:|:---|:---:|:---:|:---:|:---:|
| 1 | War in Ukraine & Russia justification | 0.7065 | 0.6570 | **0.7081** | 97 |
| 2 | Anti-EU / Europe falling apart | 0.6279 | 0.5621 | **0.6885** | 83 |
| 3 | Anti-NATO / anti-West | **0.5806** | 0.4419 | 0.5667 | 90 |
| 4 | Moldova govt & elections delegitimation | **0.4848** | 0.4615 | 0.4507 | 32 |
| 5 | Russophobia, language & identity | **0.6621** | 0.4881 | 0.5897 | 79 |
| 6 | Sanctions, energy & economy fear | **0.2500** | 0.1860 | 0.0000 | 7 |
| 7 | Transnistria / Gagauzia separatism | 0.0000 | 0.0000 | 0.0000 | 1 |
| 8 | Health, vaccines & conspiracy | **0.7600** | 0.6826 | 0.6970 | 84 |
| 9 | Traditional values & anti-LGBT | 0.6667 | 0.5556 | **0.6667** | 15 |
| 10 | Other / not disinformation (Benign) | 0.9886 | 0.9414 | **0.9912** | 396 |
| 13 | Other disinformation | 0.0435 | 0.0400 | **0.2364** | 86 |

### Quarantined Moldovan Gold Set (`gold.jsonl`)
| ID | Taxonomy Category Name | Baseline TF-IDF F1 | Frozen MiniLM F1 | Fine-Tuned MiniLM F1 | Support |
|:---:|:---|:---:|:---:|:---:|:---:|
| 1 | War in Ukraine & Russia justification | 0.1818 | 0.6667 | **0.6667** | 10 |
| 2 | Anti-EU / Europe falling apart | 0.0000 | **0.7692** | 0.5000 | 10 |
| 3 | Anti-NATO / anti-West | 0.0000 | 0.6667 | **1.0000** | 10 |
| 4 | Moldova govt & elections delegitimation | 0.0000 | **0.8333** | 0.6667 | 10 |
| 5 | Russophobia, language & identity | 0.0000 | 0.0000 | 0.0000 | 10 |
| 6 | Sanctions, energy & economy fear | 0.0000 | 0.0000 | 0.0000 | 10 |
| 7 | Transnistria / Gagauzia separatism | 0.0000 | **0.5714** | 0.0000 | 10 |
| 8 | Health, vaccines & conspiracy | 0.0000 | **0.8000** | 0.0000 | 10 |
| 9 | Traditional values & anti-LGBT | 0.0000 | **0.5714** | 0.0000 | 10 |
| 10 | Other / not disinformation (Benign) | **0.5882** | 0.7250 | 0.4832 | 40 |
| 11 | Financial panic & bank runs | 0.0000 | **0.5000** | 0.0000 | 10 |
| 12 | Forced mobilization & border militarization | 0.3297 | **0.8667** | 0.0000 | 10 |

---

## 4. Per-Language Breakdown (Romanian vs. Russian)

Evaluating cross-lingual generalization on `test.jsonl`:

| Model | Romanian Split ($N=508$) | Russian Split ($N=462$) | Romanian vs Russian Gap |
|:---|:---:|:---:|:---:|
| **Baseline TF-IDF + LR** | Macro F1: **0.5659** \| Acc: **79.9%** | Macro F1: **0.5279** \| Acc: **71.7%** | $\Delta\text{F1} = +0.0380$ |
| **Fine-Tuned MiniLM** | Macro F1: **0.5682** \| Acc: **79.7%** | Macro F1: **0.5064** \| Acc: **71.7%** | $\Delta\text{F1} = +0.0618$ |

Both models exhibit stable cross-lingual parity between Romanian and Russian. The fine-tuned transformer performs slightly better on Romanian nuance (+0.23% F1) but shows a slight drop on Russian (-2.15% F1) compared to the lexical n-gram baseline.

---

## 5. Speed vs. Resource Trade-Off

| Characteristic | Baseline TF-IDF + LR | Frozen MiniLM + LR | Fine-Tuned MiniLM Transformer |
|:---|:---:|:---:|:---:|
| **Inference Throughput (CPU)** | **6,243 texts/sec** | 23.9 texts/sec | 16.3 texts/sec |
| **Inference Latency (single item)** | **0.16 ms** | 41.8 ms | 61.3 ms |
| **Memory Footprint (RAM)** | **~35 MB** | ~380 MB | ~520 MB |
| **Storage Requirement** | **4.18 MB** | 470 MB | 448.86 MB |
| **Throughput Penalty** | 1x (Fastest) | **261x slower** | **383x slower** |

---

## 6. Error Analysis on Real Telegram Posts (`telegram_test.jsonl`)

Out of 150 Telegram posts, the fine-tuned transformer disagreed with the rule-based heuristic labels on 60 items (60.0% accuracy vs 61.3% majority baseline). Detailed manual inspection of 5 representative error cases illustrates the difference between lexical rules and semantic modeling:

### Case 1: Market News vs Economic Disinformation
- **Message ID**: `tg-msg-ch-realmorarinews-26768`
- **Text Snippet**: `🔴 Petrolul revine la 110 dolari pe baril, iar gazele se scumpesc puternic. Prețurile rămân ridicate, deși livrările din Golf și-au revenit...`
- **Heuristic Rule Label**: `6` (Sanctions, energy prices and economy fear)
- **Model Prediction**: `10` (Other / not disinformation - Benign)
- **Error Diagnosis**: **Heuristic False Positive**. The message reports objective global commodity prices (Brent crude, European natural gas exchanges). The rule-based label fired falsely due to the keyword *"gazele se scumpesc"*. The transformer correctly recognized this as standard financial market reporting.

### Case 2: Regional Poll Reporting
- **Message ID**: `tg-msg-ch-realmorarinews-26887`
- **Text Snippet**: `🔴 Moldovenii, striviți între salarii mici și scumpiri! 63% reclamă probleme financiare. Costul ridicat al vieții și veniturile...`
- **Heuristic Rule Label**: `6` (Sanctions, energy prices and economy fear)
- **Model Prediction**: `10` (Other / not disinformation - Benign)
- **Error Diagnosis**: **Borderline / Heuristic False Alarm**. A public opinion survey on purchasing power was tagged as panic-inducing disinformation by keyword matching (*"scumpiri", "probleme financiare"*). The transformer treats regional social reporting as benign news.

### Case 3: Official Debunking Reported by Media
- **Message ID**: `tg-msg-ch-realmorarinews-27406`
- **Text Snippet**: `📌 Guvernul îl acuză pe Costiuc că răspândește falsuri despre cerealele ucrainene de la Giurgiulești: „Pune în pericol securitatea...”`
- **Heuristic Rule Label**: `4` (Moldova govt & elections delegitimation)
- **Model Prediction**: `10` (Other / not disinformation - Benign)
- **Error Diagnosis**: **Heuristic Inversion Error**. The government spokesperson explicitly *denounced* a false claim about grain transshipment. The keyword heuristic saw *"Guvernul"* and *"falsuri"* and marked it as government delegitimation. The model correctly classified the article as factual reporting of an official press briefing.

### Case 4: Diplomatic Quotation
- **Message ID**: `tg-msg-ch-realmorarinews-26851`
- **Text Snippet**: `🇺🇸 Soluționarea conflictului dintre Rusia și Ucraina este mai aproape ca oricând, a declarat Donald Trump. „Ne apropiem de...”`
- **Heuristic Rule Label**: `1` (War in Ukraine & Russia justification)
- **Model Prediction**: `10` (Other / not disinformation - Benign)
- **Error Diagnosis**: **Context Misalignment**. Quoting foreign electoral/diplomatic statements is factual news reporting, not pro-Kremlin military justification propaganda. The transformer's benign classification is clinically more accurate than the naive keyword trigger.

### Case 5: International EU Accession Analysis
- **Message ID**: `tg-msg-ch-wtfmoldova-94042`
- **Text Snippet**: `⚡️ Politico: ЕС может разделить процессы вступления Молдовы и Украины. Европейская комиссия готовит для Украины более острый...`
- **Heuristic Rule Label**: `1` (War in Ukraine)
- **Model Prediction**: `10` (Other / not disinformation - Benign)
- **Error Diagnosis**: Quoting a *Politico* report on EU enlargement negotiations was triggered as Ukraine war narrative due to the word *"Украины"*. The model classifies it as neutral international politics.

---

## 7. Strategic Synthesis & Findings

1. **The Gold Set Proves Semantic Value**:
   - On the Quarantined Moldovan Gold Set (`gold.jsonl`), lexical TF-IDF completely fails (Macro F1 = **0.0916**) because regional phrasing and dialectical terms ("ordonanță", "mobilizare forțată", "marionete occidentale") were not in the Romanian fact-checking training dictionary.
   - Dense multilingual representations (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) solve this zero-shot generalization gap, jumping to Macro F1 = **0.5806** [0.4970, 0.6394] (+533%).

2. **The Telegram Domain Gap & The False Positive Threat**:
   - Standalone dense models produce significant false positive rates on neutral news (**55.8%** FPR for frozen encoder, **10.8%** FPR for fine-tuned transformer) when evaluated without thresholding or keyword gating.
   - Real Telegram broadcasts are predominantly neutral or regional news (61.3% benign). Naively deploying an uncalibrated dense neural classifier on Telegram feeds causes severe alert fatigue by flagging standard energy, political, and diplomatic reporting.

3. **The Hybrid Pipeline is Superior to Any Standalone Model**:
   - When models are integrated into the full ScamGuard architecture (`NarrativeClassifierService`), which combines keyword validation, semantic prototype alignment, debunk retrieval, and ML output:
     - The hybrid pipeline with **TF-IDF + LR** at calibrated threshold $\tau=0.38$ delivers the highest overall balance: **0.4429** Macro F1 and **67.3%** Accuracy on Telegram, **0.4543** Macro F1 on Gold, and **15.8%** FPR on hard negatives, processing **58.8 texts/sec**.
     - Dense sentence embeddings (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) provide the highest standalone semantic recall on dialectal claims, making them ideal as an embedding feature extractor or second-stage reranker.

---

## 8. Final Recommendation

> [!IMPORTANT]
> **Recommendation: Maintain Hybrid Baseline with Dense Similarity Retained for Retrieval.**
> 
> 1. **Do NOT replace the production classifier with a standalone fine-tuned transformer.**
>    - The fine-tuned transformer is **383x slower** on CPU (16 texts/s vs 6,243 texts/s) and requires 448 MB of memory without exceeding the hybrid baseline's accuracy on real Telegram broadcasts (60.0% vs 67.3%).
>    - Full XLM-RoBERTa / DeBERTa fine-tuning on CPU proved computationally prohibitive (>2 hours/epoch), making edge CPU deployment impractical.
> 2. **Keep the TF-IDF + Logistic Regression model as the primary learned classifier.**
>    - It offers sub-millisecond latency (6,243 texts/sec), zero hallucination risk, and strict 0.0% standalone false positive rate on neutral news.
> 3. **Leverage Multilingual MiniLM for Debunk Retrieval & Prototype Alignment (Signals 2 & 3).**
>    - The dense encoder's strength lies in semantic similarity (proven by the 0.5806 Gold Set F1). It is best utilized in ScamGuard as the dense index for matching incoming Telegram posts against known StopFals.md / EUvsDisinfo fact-check debunks, while letting the hybrid multi-signal gate make the final call.
