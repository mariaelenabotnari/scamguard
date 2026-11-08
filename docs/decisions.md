# Dataset Architecture & Taxonomy Decisions

This document details the architectural decisions and taxonomy strategy for ScamGuard's multi-lingual narrative classifier dataset (`v1`).

---

## 1. Class Taxonomy & Handling of Low-Resource Classes

| Category ID | Name | Target Train Goal | Status / Decision | Notes |
|---|---|---|---|---|
| **1** | War in Ukraine and Russia justification | $\ge 150$ | High Resource | Abundant coverage across EUvsDisinfo, Telegram, and news debunks (RU & RO). |
| **2** | Anti-EU / "Europe is falling apart" | $\ge 150$ | High Resource | Abundant coverage in debunks, Moldovan political channels, EUvsDisinfo. |
| **3** | Anti-NATO / anti-West | $\ge 150$ | High Resource | High volume across Western warmongering, missile deployment narratives. |
| **4** | Moldova government and elections delegitimisation | $\ge 150$ | High Resource | Critical core narrative for Moldovan 2024–2025 election and referendum security. |
| **5** | Russophobia, language and identity | $\ge 150$ | High Resource | Widely propagated identity narrative in Transnistria, Balti, and northern Moldova. |
| **6** | Sanctions, energy prices and economy fear | $\ge 150$ | High Resource | High volume regarding gas debt (Moldovagaz/Gazprom), tariff increases. |
| **7** | Transnistria / Gagauzia and separatism | $\ge 150$ | High Resource | Specific regional security narrative; high coverage in local channels. |
| **8** | Health, vaccines and conspiracy | $\ge 150$ | High Resource | Biolabs in Ukraine/Moldova, WHO pandemic treaty, vaccine panic. |
| **9** | Traditional values, religion, anti-LGBT narratives | $\ge 150$ | High Resource | Orthodox Church narratives, anti-EU LGBT rhetoric. |
| **10** | Other / not disinformation (Benign) | $\ge 800$ | Very High Resource | MOROCO (culture, sports, science, tech) + Russian news + benign Telegram posts. |
| **11** | Financial panic, bank runs and currency devaluation | $\ge 100$ | **Low-Resource (Targeted Few-Shot / Retrieval)** | Acute event-driven panic campaigns that flare up in short waves (e.g. Moldindconbank / MAIB bank run rumors). Maintained as distinct class using retrieval prototype augmentation and synthetic back-translation. |
| **12** | Forced mobilization and border militarization | $\ge 100$ | **Low-Resource (Targeted Few-Shot / Retrieval)** | Event-driven military mobilization rumors (e.g. false reservist draft orders, Romanian annexation). Handled via focused retrieval prototypes and cross-lingual augmentation rather than merging, to ensure high sensitivity to mobilization hoaxes. |
| **13** | Other disinformation (Unclassified / General) | $\ge 150$ | High Resource | **New class introduced** to prevent unclassified disinformation from being erroneously mapped into class 10 (Benign). Captures global conspiracies and foreign conflicts. |

---

## 2. Anti-Leakage Policy (`group_id`)
To prevent test set contamination:
1. Every claim is assigned a deterministic `group_id` based on canonicalized MinHash fingerprinting and semantic embedding clustering.
2. Direct translations (RO $\leftrightarrow$ RU), paraphrases, and near-duplicates share the exact same `group_id`.
3. The dataset builder partitions by `group_id` (grouped stratification) so that no group ever straddles the train, validation, test, or gold evaluation sets.
4. An automated test (`ml/tests/test_no_leakage.py`) asserts that the intersection of group IDs between splits is strictly empty.

---

## 3. Separation of Moldovan Gold Benchmark Set
- The Moldovan Gold Test Set (`gold.jsonl`) is collected from independent Telegram monitoring timeframes and verified fact-check claims.
- It is strictly quarantined: never used for training or validation threshold tuning.

---

## 4. Pre-Registered Model Replacement & Hybrid Gate Decision Rule (Round 2)

This decision rule is recorded **prior to training and evaluating the Round 2 candidate architectures (Approaches A, B, C, and D)** to prevent post-hoc threshold or metric selection.

### 4.1 Hard Gate 1 — Benign False Positive Rate Ceiling ($X = 5.0\%$)
- A candidate model (standalone or integrated into `NarrativeClassifierService`) is eligible to become the production default **only if** its False Positive Rate (FPR) on the **independent second hard-negative benchmark (`ml/eval/hard_negatives_v2.jsonl`, $N = 160$)** is **at most $5.0\%$** ($\le 8 / 160$ false alarms), reported alongside its exact two-sided 95% Clopper-Pearson binomial confidence interval.
- Rationale: `ml/eval/hard_negatives.jsonl` ($N = 120$) was found during the Round 2 audit to be 100% contaminated with `train.jsonl` items (including 50 mislabeled `FAKEROM` disinformation articles). Therefore, `ml/eval/hard_negatives_v2.jsonl`—built from held-out neutral Telegram posts and Moldovan institutional/newsroom dispatches on sensitive topics with zero training overlap—serves as the binding false-alarm gate.

### 4.2 Hard Gate 2 — Primary Ranking Metric & Tie-Breaker
Among all models passing Hard Gate 1 ($\text{FPR}_{\text{v2}} \le 5.0\%$):
1. **Primary Criterion**: Highest **Macro F1** on the **human-labeled Telegram evaluation set** (`ml/data/labeling/telegram_blind_batch.csv`, $N = 150$). Until the human-labeled CSV is returned, models are provisionally compared on held-out `test.jsonl` Macro F1 and deduplicated `gold.jsonl` Macro F1, and no production default switch is finalized on keyword-script Telegram labels alone.
2. **Tie-Breaker**: Highest **Macro F1** on the **Moldovan Gold Set (`gold.jsonl`)**, reported on both the full 150-item file and the deduplicated 30 unique base templates (`gold[:30]`).

### 4.3 Hard Gate 3 — Paired Bootstrap Significance & Parsimony Rule
- Let $\Delta \text{F1} = \text{Macro F1}(\text{Candidate}) - \text{Macro F1}(\text{Baseline})$ be computed over $B = 1{,}000$ paired bootstrap resamples (seed `42`).
- A more complex model replaces the simpler baseline (`TF-IDF + LogisticRegression`) **only if the 95% paired bootstrap confidence interval for $\Delta \text{F1}$ strictly excludes zero** ($\text{CI}_{2.5\%}(\Delta \text{F1}) > 0$).
- If $0 \in [\text{CI}_{2.5\%}(\Delta \text{F1}), \text{CI}_{97.5\%}(\Delta \text{F1})]$, the simpler model is retained as the default.

### 4.4 Hybrid Multi-Signal Gate Fix Rule (Tuned Strictly on `val.jsonl`)
- In the Round 2 audit (Section 2.1 Q2), all 19 false alarms of `NarrativeClassifierService` on `hard_negatives.jsonl` (and 47/160 on `hard_negatives_v2.jsonl`) occurred when **zero** debunk matches (`debunk_sim = 0.0`) and **low** ML disinformation probability (`ml_prob < 0.17`, while `ml_prob(Benign Cat 10) = 0.55–0.86`) were overridden by lexical keyword hits (`distinct_kw_hits >= 1`) plus `DeterministicMultilingualEmbedder` prototype similarity (`proto_sim >= 0.35`).
- Because both `distinct_kw_hits` and `DeterministicMultilingualEmbedder` prototype similarity are derived from the same hand-crafted keyword stems, counting `distinct_kw_hits >= 1` and `proto_sim >= 0.35` as two independent signals double-counts a single lexical topic match.
- **Validation-tuned rule (`val.jsonl` only)**:
  1. Fix `_load_curated_debunks` / `classify_one` to read `nearest_debunk.get("primary_label") or nearest_debunk.get("category_id")` so the 500-item debunk index actually participates in signal corroboration.
  2. Treat keyword hits and lexicon prototype similarity as **one** lexical topic signal (`lexical_signal`), requiring corroboration from either the learned ML classifier (`ml_prob >= 0.28` and `ml_prob > ml_probs.get(10, 0.0) * 0.5`) or a verified debunk match (`debunk_sim >= 0.68`) whenever the ML classifier predicts `Benign (Cat 10)` as the dominant class (`ml_probs.get(10, 0.0) >= 0.45`).

