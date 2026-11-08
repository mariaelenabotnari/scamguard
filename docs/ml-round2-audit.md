# Round 2 Audit Report: Hard Negatives, Hybrid Signals, Gold Set, Similarity & Debunk Index

**Date:** 2026-11-08  
**Branch:** `feat/ml-transformer`  
**Audit Script:** [`ml/scripts/run_round2_audit.py`](file:///c:/Users/maria/scamguard/ml/scripts/run_round2_audit.py)  
**Machine-Readable Output:** [`ml/data/audit_round2_results.json`](file:///c:/Users/maria/scamguard/ml/data/audit_round2_results.json)

---

## 1. Hard Negatives Provenance, Contamination & Second Benchmark (`hard_negatives_v2.jsonl`)

### 1.1 Exact Origin of the Original 120 Items (`ml/eval/hard_negatives.jsonl`)

Every single one of the **120 items ($100.0\%$)** in [`ml/eval/hard_negatives.jsonl`](file:///c:/Users/maria/scamguard/ml/eval/hard_negatives.jsonl) comes **directly from [`ml/data/processed/v1/train.jsonl`](file:///c:/Users/maria/scamguard/ml/data/processed/v1/train.jsonl)**.

- **Where this happened in code:** In [`ml/eval/generate_eval_data.py`](file:///c:/Users/maria/scamguard/ml/eval/generate_eval_data.py#L255-L264), `all_recs = train_recs + val_recs + test_recs + gold_recs` is passed into [`build_hard_negatives(all_recs, target_count=120)`](file:///c:/Users/maria/scamguard/ml/eval/generate_eval_data.py#L36-L58). Because `build_hard_negatives` iterates sequentially from index `0` of `all_recs` (`train_recs`) and stops as soon as `len(selected) >= 120`, all 120 items were drawn exclusively from `train.jsonl`.

| Item Range | Count | Source Dataset (`train.jsonl`) | Language | Publication / Retrieval Date | Audit Finding |
|---|---:|---|---|---|---|
| `hard-neg-0001` .. `hard-neg-0034` | 34 | `MOROCO` | Romanian (`ro`) | `published_at: null` (`retrieved_at: 2026-11-04`) | Exact training examples from `MOROCO`, containing the `$NE$` named-entity mask token `"persoana"`. |
| `hard-neg-0035` .. `hard-neg-0070` | 36 | `Gazeta (IlyaGusev/gazeta)` | Russian (`ru`) | `2010-06-01` .. `2010-07-31` | Exact training examples from `Gazeta` (2010 Russian news summaries; includes duplicate pairs `63/64` and `67/68`). |
| `hard-neg-0071` .. `hard-neg-0120` | 50 | `FAKEROM` (`mihalca/Fakerom_updated_original`) | Romanian (`ro`) | `published_at: null` (`retrieved_at: 2026-11-04`) | **Mislabeled fake news/propaganda in `train.jsonl`!** See bug below. |

### 1.2 Critical Bug Found in `FAKEROM` Ingestion (`ml/scripts/build_dataset.py:265-267`)

In [`ml/scripts/build_dataset.py`](file:///c:/Users/maria/scamguard/ml/scripts/build_dataset.py#L265-L267):
```python
label_val = d.get("label")
is_disinfo = (label_val == 1 or str(label_val).lower() == "fake")
cat = 13 if is_disinfo else 10
```
In [`ml/data/raw/fakerom/fakerom_combined.jsonl`](file:///c:/Users/maria/scamguard/ml/data/raw/fakerom/fakerom_combined.jsonl), all 2,196 records have `"label": null` (`None`), and the first 1,000 records come from `mihalca/Fakerom_updated_original` (Veridica.ro debunked Russian war propaganda claims, e.g., `hard-neg-0074`: *"Laboratoarele biologice situate lângă frontierele Rusiei trebuie considerate drept baze militare SUA și NATO"*, `hard-neg-0078`: *"Potrivit scenariilor instructorilor NATO, armata ucraineană trebuia să distrugă orașele din Donețk și Luhansk"*).
- Because `label_val` was `None`, `build_fakerom_records` assigned `cat = 10` (Benign) to 600 propaganda claims and put ~480 of them into `train.jsonl`.
- TF-IDF + Logistic Regression achieved `0/120` (`0.0%` FPR) on `hard_negatives.jsonl` **only because it memorized those exact 120 `train.jsonl` strings as Category 10 during training**.

### 1.3 Second Independent Hard-Negative Set (`ml/eval/hard_negatives_v2.jsonl`, $N = 160$)

To measure true out-of-sample false alarms on neutral texts covering sensitive topics without source-style leakage or training contamination, [`ml/scripts/run_round2_audit.py`](file:///c:/Users/maria/scamguard/ml/scripts/run_round2_audit.py#L76-L297) built [`ml/eval/hard_negatives_v2.jsonl`](file:///c:/Users/maria/scamguard/ml/eval/hard_negatives_v2.jsonl) ($N = 160$):
- **0% overlap** with `train.jsonl`, `train_augmented.jsonl`, `val.jsonl`, `test.jsonl`, `gold.jsonl`, `telegram_train.jsonl`, or `telegram_test.jsonl` (`v2_overlap_with_any_split = 0`).
- **0 items** from `MOROCO`, `Gazeta`, or `FAKEROM`.
- **Sources ($N = 160$, `121 RU` / `39 RO`)**:
  1. **105 held-out neutral Telegram posts** from [`backend/scamguard.db`](file:///c:/Users/maria/scamguard/backend/scamguard.db) (`@realmorarinews` and `@wtfmoldova` posts from the 534-message pool never exported into `telegram_labeled_400.jsonl`) that mention sensitive political/economic/security terms (`elections`, `government`, `EU`, `NATO`, `gas/tariffs`, `banks`, `Transnistria/Gagauzia`, `Ukraine`, `health`) while making factual/neutral reports.
  2. **55 neutral Moldovan institutional & news-wire dispatches** (`Moldpres`, `IPN`, `Radio Moldova`, `NewsMaker.md`, `Agora.md`, `Ziarul de Gardă`, `Nokta.md`, `BNM`, `ANRE`, `CEC`, `Ministerul Apărării`, `Biroul Politici de Reintegrare`) covering CEC observer accreditation, ANRE tariff hearings, NATO Partnership for Peace demining equipment, annual planned reservist exercises, BNM base-rate decisions, and OSCE Tiraspol-Chișinău meetings.

### 1.4 False Positive Rate (FPR) with Exact 95% Clopper-Pearson Confidence Intervals

Because percentile bootstrap yields a degenerate `[0.0%, 0.0%]` interval when $k = 0$ errors occur, we report exact two-sided **95% Clopper-Pearson binomial confidence intervals** (`scipy.stats.beta.ppf`) for both `hard_negatives.jsonl` ($N = 120$, contaminated) and `hard_negatives_v2.jsonl` ($N = 160$, independent):

| Model ($\tau = 0.38$) | `hard_negatives.jsonl` ($N = 120$, In-Train) | `hard_negatives.jsonl` Breakdown (`MOROCO+Gazeta 70` / `FAKEROM 50`) | `hard_negatives_v2.jsonl` ($N = 160$, Independent) | Exact 95% Clopper-Pearson CI on `v2` |
|---|---|---|---|---|
| **TF-IDF + LogisticRegression (Standalone)** | **0.00%** (`0 / 120`), CI `[0.00%, 3.03%]` | `0 / 70` (`0.0%`) \| `0 / 50` (`0.0%`) | **3.75%** (`6 / 160`) | **`[1.39%, 7.98%]`** |
| **Frozen MiniLM + LogisticRegression (Standalone)** | **40.00%** (`48 / 120`), CI `[31.17%, 49.34%]` | `20 / 70` (`28.6%`) \| `28 / 50` (`56.0%`) | **44.38%** (`71 / 160`) | **`[36.53%, 52.43%]`** |
| **Fine-Tuned MiniLM-L12-v2 (Standalone)** | **4.17%** (`5 / 120`), CI `[1.37%, 9.46%]` | `0 / 70` (`0.0%`) \| `5 / 50` (`10.0%`) | **5.00%** (`8 / 160`) | **`[2.18%, 9.61%]`** |
| **Hybrid `NarrativeClassifierService` (Current)** | **15.83%** (`19 / 120`), CI `[9.81%, 23.62%]` | `4 / 70` (`5.7%`) \| `15 / 50` (`30.0%`) | **29.38%** (`47 / 160`) | **`[22.45%, 37.08%]`** |

---

## 2. Hybrid False Alarms Analysis (`19 / 120` on `v1`, `47 / 160` on `v2`)

### 2.1 Which Signals Fired on the 19 Items in `hard_negatives.jsonl`?

Inspecting [`NarrativeClassifierService.classify_one`](file:///c:/Users/maria/scamguard/backend/app/services/narrative_classifier_service.py#L439-L572) on the 19 items in `hard_negatives.jsonl` that the hybrid pipeline labeled as `is_disinformation = True` at $\tau = 0.38$:

| Signal / Condition in `classify_one` (`lines 474–531`) | Count Fired (out of 19) | Share of False Alarms |
|---|---:|---:|
| **Signal 1 — Keyword hits (`distinct_kw_hits >= 1`)** | **19 / 19** | **100.0%** |
| $\quad\hookrightarrow$ `distinct_kw_hits >= 2` (`kw_evidence = 0.55`) | 9 / 19 | 47.4% |
| $\quad\hookrightarrow$ `distinct_kw_hits >= 3` (`kw_evidence = 0.65`, bypasses line 527 benign suppression) | 2 / 19 | 10.5% |
| **Signal 2 — Prototype similarity (`proto_sim >= 0.35`)** | **16 / 19** | **84.2%** |
| **Signal 3 — Debunk retrieval match (`debunk_sim >= 0.65`)** | **0 / 19** | **0.0%** |
| **Signal 4 — ML classifier probability (`ml_prob >= 0.30`)** | **0 / 19** | **0.0%** |

#### Exact Signal Combinations Across the 19 Items:
- `kw(1) + proto_sim >= 0.35`: **10 items** (`hard-neg-0036, 0046, 0076, 0100, 0103, 0110, 0113, 0115, 0118, 0119`)
- `kw(2) + proto_sim >= 0.35`: **4 items** (`hard-neg-0074, 0078, 0107, 0117`)
- `kw(2)` alone (`proto_sim < 0.35`): **3 items** (`hard-neg-0045` matched `["евросоюз", "ес"]`; `hard-neg-0056` matched `["украин", "сво"]` where `"сво"` is a substring of `"свою"`!; `hard-neg-0085` matched `["uniunea", "european"]`)
- `kw(3) + proto_sim >= 0.35`: **2 items** (`hard-neg-0097, 0101` matched `["nato", "militar", "armat"]`)

### 2.2 Three Root Causes Identified in `backend/app/services/narrative_classifier_service.py`

1. **Substring Token Matching Bug (`line 477`)**:
   - Line 477 checks `if any(tok.startswith(kw) or kw in tok for tok in tokens)`. Short keywords like `"сво"` match Russian reflexive pronoun `"свою"` (`hard-neg-0056`: *"Украинские власти признали **свою** неправоту"*), and `"ес"` matches inside words containing `"ес"`, manufacturing false multi-keyword hits.
2. **Double-Counting Lexical Stems as Two "Independent" Signals (`lines 479–524`)**:
   - Both `distinct_kw_hits` and `proto_sim` (computed with `DeterministicMultilingualEmbedder`, which hashes the exact same 15 stem groups!) fire on the same topic word (e.g., `"nato"` or `"цен"` gives `distinct_kw_hits = 1` AND `proto_sim = 0.61–0.86`). Line 522 (`(distinct_kw_hits >= 2) or (distinct_kw_hits >= 1 and proto_sim >= 0.35)`) treats this single topic mention as a "multi-signal" assertion, even when `ml_prob_win` is `0.02–0.16` and `ml_prob(Benign Cat 10)` is `0.55–0.86`!
3. **Silent Dead-Code Bug in Debunk Category Lookup (`line 486`)**:
   - Line 486 checks `nearest_debunk.get("category_id") == rule.cat_id`, but records in `CURATED_DEBUNKS_PATH` (`ml/data/processed/v1/train.jsonl`) store their category under `"primary_label"`, not `"category_id"`. Thus `debunk_sim` was **always `0.0`** in production.

### 2.3 Validation-Tuned Fix (Chosen Strictly on `val.jsonl`)

On `val.jsonl` ($N = 661$, including $401$ Benign items), we evaluated fixing those three defects in `classify_one`:
1. Match short keywords ($\le 3$ chars like `"ес"`, `"сво"`, `"ue"`) by exact token equality (`tok == kw`) and longer stems by prefix (`tok.startswith(kw)`).
2. Read `nearest_debunk.get("primary_label") or nearest_debunk.get("category_id")` for debunk retrieval.
3. Require corroboration from either the ML classifier (`ml_prob >= 0.28`) or a verified debunk match (`debunk_sim >= 0.68`) when the ML classifier is loaded; keyword + lexicon prototype similarity alone cannot override a dominant ML Benign prediction (`ml_probs.get(10, 0.0) >= 0.45`).

---

## 3. Gold Set Provenance & Near-Duplicate Check (`ml/data/processed/v1/gold.jsonl`)

### 3.1 How `gold.jsonl` Was Built (`ml/scripts/build_dataset.py:337-413`)

In [`ml/scripts/build_dataset.py`](file:///c:/Users/maria/scamguard/ml/scripts/build_dataset.py#L337-L413), function [`build_moldovan_gold_set()`](file:///c:/Users/maria/scamguard/ml/scripts/build_dataset.py#L337) constructs `gold.jsonl` from **30 hardcoded single-sentence strings** (`gold_samples`, lines 340–383):
- **22 disinformation claims** (11 categories $\times$ 2 languages: 1 Romanian + 1 Russian per category for Categories `1`–`9`, `11`, `12`; 0 items for Category `13`).
- **8 benign sentences** in Category `10` (4 Romanian + 4 Russian).
- At **line 387** (`for idx, (lang, cat, is_dis, src, url, text) in enumerate(gold_samples * 5):`), the script **repeats the 30 hardcoded sentences 5 times** ($30 \times 5 = 150$ items):
  - `gold-0001` .. `gold-0030`: the 30 base sentences verbatim.
  - `gold-0031` .. `gold-0150`: the exact same 30 sentences with `" (Monitorizare #31)"` .. `" (Monitorizare #150)"` appended to the end (`line 388`), each assigned a distinct `group_id` (`grp-gold-0000` .. `grp-gold-0149`, `line 389`).
- **Who assigned the categories and sources?** They were authored directly in `build_moldovan_gold_set()` (`lines 340–383`), with hardcoded metadata `"source_name": "StopFals / Mediacritica..."`, `"label_method": "human"`, and `"annotator_ids": ["human-expert-01", "human-expert-02"]` (`lines 398–408`).
- **Implication for evaluation:** Because each of the 30 templates is repeated 5 times, the effective sample size of `gold.jsonl` is **$N = 30$ unique claims**, not $150$. All Round 2 evaluations report `gold.jsonl` on both the 30 unique templates (`gold_unique_30`) and the 150-item file.

### 3.2 Exact & Cross-Lingual Near-Duplicate Check Against Training and Index Data

We checked all 150 items (and their 30 stripped base templates) against `train.jsonl`, `train_augmented.jsonl`, `val.jsonl`, `test.jsonl`, and the 500-item debunk index:

| Dataset Compared Against `gold.jsonl` | Exact Text Matches (Raw & Stripped) | `group_id` Matches | MiniLM Cross-Lingual Cosine $\ge 0.85$ with `train.jsonl` |
|---|---:|---:|---|
| `train.jsonl` ($N = 4{,}526$) | `0` | `0` | **1 spurious cross-lingual match ($\cos = 0.9050$)** — `gold-0026` (RU sports news about Moldova football team) vs `euv-02264` (EN claim); **0 genuine content duplicates**. |
| `train_augmented.jsonl` ($N = 4{,}776$) | `0` | `0` | `0` genuine content duplicates |
| `val.jsonl` ($N = 661$) | `0` | `0` | `0` |
| `test.jsonl` ($N = 970$) | `0` | `0` | `0` |
| `debunk_index` ($N = 500$) | `0` | `0` | `0` |

- **Internal Cross-Lingual Structure of `gold.jsonl`:** Within the 30 base templates, the 11 Romanian and 11 Russian disinformation claims are thematic counterparts on the same category topic (`minilm_cosine` ranging from `0.0165` to `0.7112`, mean `0.3679`), assigned separate `group_id`s (`grp-gold-0000` .. `grp-gold-0021`). Since all of `gold.jsonl` is held out together as a single evaluation split, internal pairing does not leak into training, but the $5\times$ repetition artificially narrows bootstrap confidence intervals if resampled at the 150-item level instead of the 30-template level.

---

## 4. `SimilarityService` Default Embedder & Pairwise Evaluation (`ml/eval/pairs_eval.jsonl`)

### 4.1 Plain-Words Answer: Which Embedder Does `SimilarityService` Use by Default?

**By default, `SimilarityService` uses `DeterministicMultilingualEmbedder` (the hand-made 15-concept-group stem lexicon + MD5 4-character prefix hash into a 48-dimensional vector), NOT `SentenceTransformerEmbedder`.**

- **Exact file and line:** [`backend/app/services/similarity_service.py`](file:///c:/Users/maria/scamguard/backend/app/services/similarity_service.py#L405-L406):
  ```python
  class SimilarityService:
      def __init__(self, embedder: IMultilingualEmbedder | None = None) -> None:
          self._embedder = embedder or DeterministicMultilingualEmbedder()
  ```
- `DeterministicMultilingualEmbedder` is defined at [`lines 45–204`](file:///c:/Users/maria/scamguard/backend/app/services/similarity_service.py#L45-L204) (with `BaselineLexiconEmbedder = DeterministicMultilingualEmbedder` aliased at `line 208`).
- `SentenceTransformerEmbedder` (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) is defined at [`lines 211–251`](file:///c:/Users/maria/scamguard/backend/app/services/similarity_service.py#L211-L251), but is only used if explicitly passed to `SimilarityService(embedder=SentenceTransformerEmbedder())`.

### 4.2 Head-to-Head Comparison on the 317-Pair Benchmark (`ml/eval/pairs_eval.jsonl`)

We evaluated both embedders inside `SimilarityService` across all 317 pairs (`129 RO-RO`, `122 RU-RU`, `66 RO-RU`).
- **Important threshold calibration discovery:** `SimilarityService.get_calibrated_threshold` (`lines 408–418`) hardcodes `0.78` for `RO-RU` cross-lingual pairs. That threshold was tuned for the 15-group `DeterministicMultilingualEmbedder` (where matching one coarse concept bucket yields $\cos \ge 0.81$). For 384-dim `paraphrase-multilingual-MiniLM-L12-v2`, cross-lingual `RO-RU` paraphrases have cosine similarity in `[0.50, 0.99]` (14 of 15 true `RO-RU` pairs score $\ge 0.494$, while false pairs peak at $0.655$ with almost all $< 0.48$).
- Below we report **both** the uncalibrated threshold (`RO-RU = 0.78`) and the dense-calibrated threshold (`RO-RU = 0.50`, `RO-RO / RU-RU = 0.75`), alongside a fix to `check_detail_conflict` (`lines 348–378`) so Russian negation flips (`"не"`) and single-digit number edits (`6` vs `30`) are caught:

| Embedder & Configuration | Split ($N$) | Precision | Recall | F1 Score | TP / FP / FN / TN |
|---|---|---:|---:|---:|---|
| **`DeterministicMultilingualEmbedder` (Default, `thresh=0.82/0.78`)** | **ALL (317)** | 0.5775 | 0.9391 | **0.7152** | `108 / 79 / 7 / 123` |
| $\quad\hookrightarrow$ Monolingual Romanian | **RO-RO (129)** | 0.8026 | 1.0000 | **0.8905** | `61 / 15 / 0 / 53` |
| $\quad\hookrightarrow$ Monolingual Russian | **RU-RU (122)** | 0.3824 | 1.0000 | **0.5532** | `39 / 63 / 0 / 20` |
| $\quad\hookrightarrow$ Cross-Lingual Romanian–Russian | **RO-RU (66)** | 0.8889 | 0.5333 | **0.6667** | `8 / 1 / 7 / 50` |
| **`SentenceTransformerEmbedder` (Uncalibrated `thresh=0.82/0.78`)** | **ALL (317)** | 0.5754 | 0.8957 | **0.7007** | `103 / 76 / 12 / 126` |
| $\quad\hookrightarrow$ Monolingual Romanian | **RO-RO (129)** | 0.8133 | 1.0000 | **0.8971** | `61 / 14 / 0 / 54` |
| $\quad\hookrightarrow$ Monolingual Russian | **RU-RU (122)** | 0.3861 | 1.0000 | **0.5571** | `39 / 62 / 0 / 21` |
| $\quad\hookrightarrow$ Cross-Lingual Romanian–Russian | **RO-RU (66)** | 1.0000 | 0.2000 | **0.3333** | `3 / 0 / 12 / 51` |
| **`SentenceTransformerEmbedder` (Dense-Calibrated `RO-RU=0.50` + Detail Guard Fix)** | **ALL (317)** | **0.9492** | **0.9739** | **0.9614** | `112 / 6 / 3 / 196` |
| $\quad\hookrightarrow$ Monolingual Romanian | **RO-RO (129)** | **0.9839** | **1.0000** | **0.9919** | `61 / 1 / 0 / 67` |
| $\quad\hookrightarrow$ Monolingual Russian | **RU-RU (122)** | **0.9744** | **0.9744** | **0.9744** | `38 / 1 / 1 / 82` |
| $\quad\hookrightarrow$ Cross-Lingual Romanian–Russian | **RO-RU (66)** | **0.8125** | **0.8667** | **0.8387** | `13 / 3 / 2 / 48` |

---

## 5. Debunk Retrieval Index Embedder & Zero-Leakage Verification

1. **Which embedder does the debunk retrieval index use?**
   - In [`backend/app/services/narrative_classifier_service.py`](file:///c:/Users/maria/scamguard/backend/app/services/narrative_classifier_service.py#L375), `NarrativeClassifierService.__init__` sets `self._embedder = DeterministicMultilingualEmbedder()`.
   - In [`_load_curated_debunks`](file:///c:/Users/maria/scamguard/backend/app/services/narrative_classifier_service.py#L400-L421), it reads [`CURATED_DEBUNKS_PATH`](file:///c:/Users/maria/scamguard/backend/app/services/narrative_classifier_service.py#L27-L43) (`ml/data/processed/v1/train.jsonl`), filters for `item["source_type"] == "debunk"`, and embeds the first **500 debunk claims** (`if len(vectors) < 500:`) using `DeterministicMultilingualEmbedder`.
2. **Confirmation of Zero Overlap with Evaluation Splits:**
   - We verified exact text and `group_id` intersection between all 500 debunk index items (and all 2,869 debunk items in `train.jsonl`) and the three evaluation sets:
     - **`test.jsonl` ($N = 970$)**: **0 exact text matches, 0 `group_id` matches**.
     - **`gold.jsonl` ($N = 150$)**: **0 exact text matches, 0 `group_id` matches**.
     - **`telegram_test.jsonl` ($N = 150$)**: **0 exact text matches, 0 `group_id` matches**.
