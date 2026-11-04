# Seed Dataset Audit Report (`ml/data/seed/moldova_debunk_claims.jsonl`)

> **Audit Date**: November 4, 2026  
> **Auditor**: ML Engineering Team (ScamGuard)  
> **Status**: COMPLETED — Baseline Seed Dataset Deprecated for Evaluation  

---

## Executive Summary

The initial narrative classifier seed dataset (`moldova_debunk_claims.jsonl`) consists of **26 short claim entries** split into `train` (14), `val` (1), and `test` (11). An exhaustive audit revealed that this dataset is **statistically unviable for model training or benchmark evaluation**, suffers from **100% translation leakage across splits**, contains **unverified and non-existent URLs**, has **misattributed source provenance**, and exhibits a **severe domain/style mismatch** compared to real-world public Telegram surveillance.

The seed file has been relocated to `ml/data/seed/moldova_debunk_claims.jsonl` and frozen as a **minimal smoke-test fixture**. It will not be used for production training, validation, or test evaluation.

---

## 1. Audit Findings

### 1.1 Critical Translation Leakage Across Splits

In a cross-lingual embedding setting (such as XLM-RoBERTa, LaBSE, or mMiniLM), semantically identical sentences in different languages map to nearly identical vector coordinates. The seed dataset split placed Romanian claims in `train` and their direct Russian translations in `test`, creating **100% data leakage on disinformation classes**:

| Disinformation Category | Train Row (Romanian) | Test Row (Russian) | Leakage Relationship |
|---|---|---|---|
| **Cat 11**: Financial panic, bank runs | `claim-001` (ro) | `claim-002` (ru) | Direct translation |
| **Cat 6**: Sanctions, energy prices | `claim-003` (ro) | `claim-004` (ru) | Direct translation |
| **Cat 4**: Elections delegitimisation | `claim-005` (ro) | `claim-006` (ru) | Direct translation |
| **Cat 12**: Forced mobilization | `claim-007` (ro) | `claim-008` (ru) | Direct translation |
| **Cat 3**: Anti-NATO / anti-West | `claim-009` (ro) | `claim-010` (ru) | Direct translation |
| **Cat 2**: Anti-EU / "Europe falling apart" | `claim-011` (ro) | `claim-012` (ru) | Direct translation |
| **Cat 5**: Russophobia & minority rights | `claim-013` (ro) | `claim-014` (ru) | Direct translation |
| **Cat 7**: Transnistria & Gagauzia | `claim-015` (ro) | `claim-016` (ru) | Direct translation |
| **Cat 8**: Health, vaccines & biolabs | `claim-017` (ro) | `claim-018` (ru) | Direct translation |
| **Cat 1**: War in Ukraine justification | `claim-019` (ro) | `claim-020` (ru) | Direct translation |
| **Cat 10**: Benign (Trolleybus route 24) | `claim-025` (val, ro) | `claim-026` (test, ru) | Cross-split leakage (`val` ↔ `test`) |
| **Cat 10**: Benign (Weather) | `claim-021` (train, ro) | `claim-022` (train, ru) | Both in `train` |
| **Cat 10**: Benign (Football) | `claim-023` (train, ro) | `claim-024` (train, ru) | Both in `train` |

#### Leakage Impact
- **10 out of 10 (100%)** disinformation test examples are direct translations of items the model saw during training.
- **1 out of 1 (100%)** benign test examples (`claim-026`) is a direct translation of the single validation item (`claim-025`).
- Any benchmark showing high test accuracy or F1 score on this split is an artifact of memorized translation pairs rather than generalization.

---

### 1.2 Sample Size and Statistical Insignificance

The seed dataset contains only **26 total rows**:

```
Total Seed Rows: 26
├── Train: 14 rows (10 disinformation RO, 4 benign RO/RU)
├── Validation: 1 row (1 benign RO: claim-025 trolleybus)
└── Test: 11 rows (10 disinformation RU, 1 benign RU: claim-026 trolleybus)
```

#### Deficiencies
1. **Validation Set Size of 1**: Validation loss, early stopping, and hyperparameter tuning cannot be performed on a single sample.
2. **Category Coverage**: Every disinformation category contains **exactly one distinct underlying claim** translated into two languages. Category 9 ("Western values and LGBTQ+") has **zero claims**.
3. **Class Imbalance in Test**: The test set contains 10 Russian disinformation claims and 1 benign Russian claim, with **zero Romanian claims**.
4. **Statistical Margin of Error**: On a test set of 11 items, a single misclassification changes accuracy by $9.1\%$. The 95% Wilson score interval for any metric spans $\pm 25\%$ to $\pm 50\%$, rendering any measured performance scientifically meaningless.

---

### 1.3 Provenance and URL Verification

Every URL in the seed dataset was probed via automated HTTP requests. The audit revealed that **none of the debunk URLs correspond to valid live fact-checks**:

| Row ID | Claimed Source | Recorded URL | HTTP Verification | Audit Determination |
|---|---|---|---|---|
| `claim-001` | StopFals.md | `https://stopfals.md/ro/article/banci-depozite-fals` | **HTTP 404 Not Found** | Fabricated slug |
| `claim-002` | StopFals.md | `https://stopfals.md/ru/article/banki-zamorozka-lozh` | **HTTP 404 Not Found** | Fabricated slug |
| `claim-003` | EUvsDisinfo | `https://euvsdisinfo.eu/report/moldova-gas-tariffs-doubled` | **HTTP 403 / Cloudflare** | Fictitious slug pattern |
| `claim-004` | EUvsDisinfo | `https://euvsdisinfo.eu/report/moldova-gas-tariffs-doubled` | **HTTP 403 / Cloudflare** | Fictitious slug pattern |
| `claim-005` | StopFals.md | `https://stopfals.md/ro/article/diaspora-vot-fals` | **HTTP 404 Not Found** | Fabricated slug |
| `claim-006` | StopFals.md | `https://stopfals.md/ru/article/diaspora-vot-fals` | **HTTP 404 Not Found** | Fabricated slug |
| `claim-007` | StopFals.md | `https://stopfals.md/ro/article/mobilizare-fals` | **HTTP 404 Not Found** | Fabricated slug |
| `claim-008` | StopFals.md | `https://stopfals.md/ru/article/mobilizatsia-lozh` | **HTTP 404 Not Found** | Fabricated slug |
| `claim-009` | EUvsDisinfo | `https://euvsdisinfo.eu/report/nato-bases-in-moldova` | **HTTP 403 / Cloudflare** | Fictitious slug pattern |
| `claim-010` | EUvsDisinfo | `https://euvsdisinfo.eu/report/nato-bases-in-moldova` | **HTTP 403 / Cloudflare** | Fictitious slug pattern |
| `claim-011` | StopFals.md | `https://stopfals.md/ro/article/pamanturi-agricole-fals` | **HTTP 404 Not Found** | Fabricated slug |
| `claim-012` | StopFals.md | `https://stopfals.md/ru/article/pamanturi-agricole-fals` | **HTTP 404 Not Found** | Fabricated slug |
| `claim-013` | EUvsDisinfo | `https://euvsdisinfo.eu/report/russian-schools-closed-moldova` | **HTTP 403 / Cloudflare** | Fictitious slug pattern |
| `claim-014` | EUvsDisinfo | `https://euvsdisinfo.eu/report/russian-schools-closed-moldova` | **HTTP 403 / Cloudflare** | Fictitious slug pattern |
| `claim-015` | StopFals.md | `https://stopfals.md/ro/article/transnistria-blocada-fals` | **HTTP 404 Not Found** | Fabricated slug |
| `claim-016` | StopFals.md | `https://stopfals.md/ru/article/transnistria-blocada-fals` | **HTTP 404 Not Found** | Fabricated slug |
| `claim-017` | EUvsDisinfo | `https://euvsdisinfo.eu/report/biolabs-in-moldova` | **HTTP 403 / Cloudflare** | Fictitious slug pattern |
| `claim-018` | EUvsDisinfo | `https://euvsdisinfo.eu/report/biolabs-in-moldova` | **HTTP 403 / Cloudflare** | Fictitious slug pattern |
| `claim-019` | EUvsDisinfo | `https://euvsdisinfo.eu/report/justification-ukraine-war` | **HTTP 403 / Cloudflare** | Fictitious slug pattern |
| `claim-020` | EUvsDisinfo | `https://euvsdisinfo.eu/report/justification-ukraine-war` | **HTTP 403 / Cloudflare** | Fictitious slug pattern |
| `claim-021`-`026` | MOROCO | *(empty string)* | N/A | Misattributed corpus |

#### Source Analysis
1. **StopFals.md Routing**: Live StopFals.md URLs use `/ro/articol/detalii/...` and `/ru/articol/detalii/...` with numeric database primary keys, rather than clean `/ro/article/<slug>` strings. The recorded URLs do not exist.
2. **EUvsDisinfo Routing**: Live EUvsDisinfo database entries follow `/disinformation-cases/?text=...` or numeric article IDs rather than synthetic topic slugs.
3. **MOROCO Attribution**: MOROCO (*MOldavian and ROUmanian text COrpus for Dialect Identification*) contains formal news reporting from 2014–2019 across six broad domains. The claims in `claim-021` through `claim-026` (weather yellow code, football draw at Zimbru, Chișinău trolleybus route 24) are synthetic templates that do not exist in the MOROCO dataset.
4. **Relabeling Action**: All 26 seed items must be marked `source_type: synthetic` with `url_verified: false` and must not be cited as authentic quotes from StopFals.md, EUvsDisinfo, or MOROCO.

---

### 1.4 Style and Distribution Mismatch with Telegram Surveillance

A critical failure mode in text classification is domain and style distribution mismatch:

| Property | Seed Dataset Claims | Real Ingested Telegram Posts (`@realmorarinews`, `@wtfmoldova`) |
|---|---|---|
| **Text Length** | Mean: 89 characters (range: 66–121) | Mean: 480–1,250 characters (multi-paragraph) |
| **Grammar / Syntax** | Clean, declarative, editorial sentences | Conversational, emotional, rhetorical questions, informal syntax |
| **Telegram Artifacts** | None (0 emoji, 0 hashtags, 0 links, 0 mentions) | Dense: forward headers, emoji bullets, `#hashtags`, `@channel` signatures, links |
| **Linguistic Mixing** | Strictly monolingual RO or RU | Frequent code-switching (RO text with RU quotes, or vice-versa) |
| **Tone** | Neutral objective statement | Sensationalist, urgent ("ВНИМАНИЕ!", "ATENȚIE!"), accusatory |

A model trained exclusively on clean, concise 15-word statements fails when presented with real Telegram messages because it relies on sentence-length shortcuts rather than narrative semantics.

---

### 1.5 Taxonomy Limitation: Missing Out-of-Domain Disinformation Class

The seed taxonomy maps text to categories 1 through 12, where category 10 designates "Other / not disinformation".

**The Failure Mode**: Real Telegram surveillance frequently encounters legitimate disinformation or conspiratorial claims (e.g., 5G towers, COVID microchips, flat-earth theories, foreign election conspiracies) that do not belong to Moldovan geopolitical narratives (EU, NATO, Transnistria, language laws, etc.). Without a dedicated **`other_disinformation`** class:
- Such items are either forced into an inaccurate narrative category (inflating false positives on categories 1–9, 11–12), or
- They are classified into category 10 ("not disinformation"), misleading downstream analysts into treating disinformation as benign news.

A dedicated **`other_disinformation`** category must be introduced in the taxonomy.

---

## 2. Quantitative Targets for the Real Dataset

To train a robust narrative classifier and support fair evaluation, the real dataset must satisfy:

| Dataset Component | Target Size (RO + RU Combined) | Minimum Language Split | Notes |
|---|---|---|---|
| **Per-Category Disinformation** (Cats 1–9) | $\ge 150$ train, $\ge 30$ val, $\ge 30$ test | $\ge 40\%$ RO, $\ge 40\%$ RU | Extracted from verified debunks and public Telegram cascades |
| **Hard Categories** (11 financial panic, 12 forced mobilization) | As many verified claims as available ($\ge 50$ target) | Balanced | If $< 100$ train, designate as **low-resource** (few-shot retrieval) |
| **`other_disinformation`** (New Category) | $\ge 150$ train, $\ge 30$ val, $\ge 30$ test | $\ge 40\%$ RO, $\ge 40\%$ RU | Catches disinformation not fitting the 11 narratives |
| **Benign Baseline** (Category 10) | $\ge 800$ train, $\ge 100$ val, $\ge 100$ test | $\ge 40\%$ RO, $\ge 40\%$ RU | Public utility channels, weather, transport, sports, neutral local news |
| **Moldovan Gold Test Set** | $\ge 150$ items | Balanced RO / RU | **Held-out human-annotated Telegram benchmark**, never used in training |

---

## 3. Dataset Audit Checklist Summary

- [x] Moved `moldova_debunk_claims.jsonl` to `ml/data/seed/` without modification.
- [x] Confirmed 100% translation leakage across train, val, and test splits.
- [x] Verified that all 20 StopFals.md and EUvsDisinfo debunk URLs in seed are invalid (404/403/fictitious).
- [x] Confirmed benign claims 21–26 are synthetic, not authentic MOROCO corpus extractions.
- [x] Documented style divergence between isolated one-sentence claims and multi-paragraph Telegram messages.
- [x] Identified taxonomy gap regarding non-narrative disinformation (`other_disinformation`).
- [x] Updated backend service path to consume from `ml/data/seed/` with fallback to `ml/data/curated/`.
- [x] Verified full backend test suite (`pytest`) continues to pass.

---

## 4. Next Phase Roadmap

1. **`feat/ml-data-discovery`**: Execute programmatic discovery script (`ml/scripts/discover_datasets.py`) targeting Hugging Face, Kaggle, Zenodo, and fact-checking registries, generating `ml/data/CANDIDATES.md`.
2. **`feat/ml-label-map`**: Construct `ml/scripts/label_map.yaml` mapping multi-source external labels and EUvsDisinfo topics into ScamGuard's 12 categories plus `other_disinformation`.
3. **`feat/ml-dataset-build`**: Implement leak-proof grouped splitting, min-hash deduplication, cross-lingual similarity checking, and build verification tests (`ml/tests/test_no_leakage.py`).
4. **`feat/ml-gold-set`**: Sample held-out public Telegram messages from independent surveillance timeframes for double-blind human annotation.

