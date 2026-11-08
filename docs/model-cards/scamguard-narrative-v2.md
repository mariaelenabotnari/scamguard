# Model Card: ScamGuard Narrative Classifier v2.1

## 1. Model Details
- **Component Name**: `scamguard-narrative-v2.1` (`NarrativeClassifierService` + `ml/models/`)
- **Version**: `v2.1.0` (Round 2 Audited & Calibrated)
- **Architecture**:
  - **Production Default Classifier**: Word + Character n-gram TF-IDF + Calibrated `LogisticRegression` (`ml/models/narrative_classifier.joblib`), retained per the pre-registered parsimony & paired-bootstrap rule in [`docs/decisions.md`](file:///c:/Users/maria/scamguard/docs/decisions.md) until human-labeled Telegram evaluation (`ml/data/labeling/telegram_blind_batch.csv`) or 3-seed GPU transformer fine-tuning (`ml/notebooks/finetune_transformers_gpu.ipynb`) demonstrates a statistically significant paired bootstrap gain at $\text{FPR}_{\text{v2}} \le 5.0\%$.
  - **Round 2 Candidate Architectures Available (`ml/models/`)**:
    - **Approach A (`stacked_tfidf_minilm.joblib`)**: Stacked TF-IDF (word 1–2-grams + char 3–5-grams) + Frozen `paraphrase-multilingual-MiniLM-L12-v2` embeddings with validation-tuned probability stacking.
    - **Approach B (`RetrievalKnnCentroidClassifier`)**: MiniLM $k$-NN + L2-normalized class centroid retrieval returning the nearest training claim text and similarity as human-readable evidence.
    - **Approach C (`twostep_tfidf_minilm.joblib`)**: Two-step hierarchical classifier (Step 1 binary disinformation vs. benign $\rightarrow$ Step 2 12-class narrative classifier using stacked features).
  - **Validation-Tuned Multi-Signal Gate (`NarrativeClassifierService.classify_one`)**:
    - Combines exact/prefix keyword matching (preventing short-token substring collisions such as `"сво"` inside `"свою"`), prototype alignment, 500-item fact-check debunk retrieval, and ML probability distribution.
    - Suppresses lexical topic false alarms on multi-clause posts ($\ge 12$ tokens) unless corroborated by the ML classifier (`ml_prob >= 0.30`) or a verified debunk claim (`debunk_sim >= 0.65`), cutting `hard_negatives_v2.jsonl` FPR from `29.38%` (`47/160`) to **`3.12%` (`5/160`, 95% Clopper-Pearson CI `[1.02%, 7.14%]`)** and `hard_negatives.jsonl` FPR from `15.83%` (`19/120`) to **`0.00%` (`0/120`, 95% CP CI `[0.00%, 3.03%]`)**.

## 2. Intended Use & Scope
- **Primary Use**: Mapping public Telegram posts and cross-channel propagation cascades in the Republic of Moldova to 13 strategic narrative categories (`narrative_match` confidence $0.0$–$1.0$), accompanied by nearest fact-check debunk citations (`StopFals.md`, `EUvsDisinfo`, `Mediacritica`).
- **Human-in-the-Loop Requirement**: Outputs `narrative_match` (never "fake news" or "truth/falsehood"). Requires at least 2 corroborating signals and human analyst review before any editorial conclusion.

## 3. 13-Category Taxonomy
1. `War in Ukraine and Russia justification`
2. `Anti-EU / "Europe is falling apart"`
3. `Anti-NATO / anti-West`
4. `Moldova government and elections delegitimisation`
5. `Russophobia, language and identity`
6. `Sanctions, energy prices and economy fear`
7. `Transnistria / Gagauzia and separatism`
8. `Health, vaccines and conspiracy`
9. `Traditional values, religion, anti-LGBT narratives`
10. `Other / not disinformation` (Benign baseline: factual news, public service updates, sports, culture, weather)
11. `Financial panic, bank runs and currency devaluation`
12. `Forced mobilization and border militarization`
13. `Other disinformation` (Unclassified / foreign conspiracy narratives)

## 4. Quantitative Benchmark Summary ($\tau = 0.38$)

| Model | `test.jsonl` ($N=970$) Macro F1 `[95% CI]` | `gold_unique_30` ($N=30$) Macro F1 `[95% CI]` | `telegram_test.jsonl` ($N=150$, Script) Macro F1 `[95% CI]` | `hard_negatives_v2.jsonl` ($N=160$) FPR `[95% CP CI]` |
|---|---|---|---|---|
| **Baseline: TF-IDF + LR (`narrative_classifier.joblib`)** | `0.3844 [0.3529, 0.4136]` | `0.0897 [0.0256, 0.1253]` | `0.1446 [0.0964, 0.1801]` | **`3.75%`** (`6/160`) `[1.39%, 7.98%]` |
| **Approach A: Stacked TF-IDF + Frozen MiniLM** | **`0.4422 [0.4028, 0.4773]`** | `0.1935 [0.0416, 0.2578]` | **`0.1910 [0.1487, 0.2228]`** | `6.25%` (`10/160`) `[3.04%, 11.19%]` |
| **Approach B: MiniLM Retrieval ($k$-NN + Centroids)** | `0.3792 [0.3468, 0.4083]` | **`0.4031 [0.1993, 0.4791]`** | **`0.1924 [0.1170, 0.2505]`** | `5.63%` (`9/160`) `[2.60%, 10.41%]` |
| **Approach C: Two-Step Hierarchical** | `0.4293 [0.3911, 0.4631]` | `0.0324 [0.0181, 0.0465]` | `0.0794 [0.0599, 0.0977]` | **`2.50%`** (`4/160`) `[0.69%, 6.28%]` |
| **Hybrid `NarrativeClassifierService` (Fixed Gate)** | `0.2638 [0.2311, 0.2900]` | `0.3205 [0.1380, 0.3858]` | `0.1390 [0.0880, 0.1728]` | **`3.12%`** (`5/160`) `[1.02%, 7.14%]` |

## 5. Known Limitations & Caveats
1. **Weak Keyword-Script Labels on `telegram_test.jsonl`**: The 400 Telegram messages (`telegram_train.jsonl` = 250, `telegram_test.jsonl` = 150) were labeled by a heuristic keyword script (`ml/scripts/label_telegram_messages.py`), not by human annotators. A blind 150-message batch (`ml/data/labeling/telegram_blind_batch.csv`) has been prepared for human ground-truth evaluation.
2. **Gold Set Template Repetition**: `ml/data/processed/v1/gold.jsonl` ($N = 150$) consists of 30 hardcoded single-sentence templates repeated $5\times$ (`gold_samples * 5`). Effective sample size is $N = 30$ unique claims (`gold_unique_30`).
3. **Legacy `hard_negatives.jsonl` Contamination & `FAKEROM` Label Defect**: All 120 items in the original `ml/eval/hard_negatives.jsonl` were drawn from `train.jsonl`, and 50 of them were `FAKEROM` disinformation claims mislabeled as Category 10 because `"label"` was `null` in `fakerom_combined.jsonl`. All false-alarm evaluations now use the independent 160-item [`ml/eval/hard_negatives_v2.jsonl`](file:///c:/Users/maria/scamguard/ml/eval/hard_negatives_v2.jsonl) with exact 95% Clopper-Pearson confidence intervals.
