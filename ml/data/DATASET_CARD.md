# ScamGuard Narrative Classifier Dataset Card (`v1`)

---

## 1. Dataset Summary
- **Dataset Name**: ScamGuard Narrative Classifier Benchmark (`v1`)
- **Version**: `1.0.0`
- **Languages**: Romanian (`ro`) and Russian (`ru`)
- **Total Samples**: 7,876 records across 4 partitions
- **Licence**: CC BY-SA 4.0 / Open Academic Research
- **Task**: Multi-class and multi-label strategic disinformation narrative classification, debunk matching, and benign news discrimination.

---

## 2. Partition Splits & Anti-Leakage Design

To prevent the cross-split contamination identified in the seed dataset audit (where Russian test claims directly leaked Romanian training claims), all partitions are constructed using **strict `group_id` isolation**:

| Partition | Total Records | Unique Group IDs | Romanian (`ro`) | Russian (`ru`) | Primary Role |
|---|---|---|---|---|---|
| **`train.jsonl`** | 5,794 | 5,725 | 3,119 (53.8%) | 2,675 (46.2%) | Core training for classifier weights & representations. |
| **`val.jsonl`** | 962 | 954 | 496 (51.6%) | 466 (48.4%) | Validation for hyperparameter tuning & threshold selection. |
| **`test.jsonl`** | 970 | 955 | 508 (52.4%) | 462 (47.6%) | Generalization benchmark on unseen claim clusters. |
| **`gold.jsonl`** | 150 | 150 | 75 (50.0%) | 75 (50.0%) | **Quarantined** Moldovan evaluation set (independent monitoring & fact-checks). |

> **Anti-Leakage Verification:**
> Verified by `ml/tests/test_no_leakage.py`: zero `group_id` overlap, zero exact text overlap, and cross-split cosine similarity strictly bounded $< 0.95$.

---

## 3. Taxonomy Categories (Class Distribution)

| ID | Category Name | Training Count | Status | Notes |
|---|---|---|---|---|
| **1** | War in Ukraine and Russia justification | 635 | High-Resource | Sourced from EUvsDisinfo & Ukrainian war debunks. |
| **2** | Anti-EU / "Europe is falling apart" | 477 | High-Resource | EU economic ruin, Schengen collapse, loss of sovereignty. |
| **3** | Anti-NATO / anti-West | 528 | High-Resource | NATO warmongering, foreign military bases, missile threats. |
| **4** | Moldova government and elections delegitimisation | 236 | High-Resource | Election fraud, diaspora vote tampering, puppet state allegations. |
| **5** | Russophobia, language and identity | 389 | High-Resource | Persecution of Russian speakers, erasure of Soviet monuments. |
| **6** | Sanctions, energy prices and economy fear | 55 | Medium-Resource | Gas shutoffs, tariff spikes, economic collapse. |
| **7** | Transnistria / Gagauzia and separatism | 7 | Low-Resource | Specific regional flashpoint; supplemented by gold benchmarks. |
| **8** | Health, vaccines and conspiracy | 460 | High-Resource | Secret biolabs, WHO pandemic treaties, vaccine panic. |
| **9** | Traditional values, religion, anti-LGBT narratives | 93 | Medium-Resource | Orthodox Church defense, anti-LGBT rhetoric. |
| **10** | Other / not disinformation (Benign) | 2,409 | High-Resource | Authentic newsroom articles (MOROCO) + Russian news (Gazeta). |
| **11** | Financial panic, bank runs and currency devaluation | 2 | Low-Resource | Acute event-driven bank run rumors. Evaluated via few-shot retrieval. |
| **12** | Forced mobilization and border militarization | 2 | Low-Resource | Fabricated draft orders. Evaluated via few-shot retrieval. |
| **13** | Other disinformation (Unclassified / General) | 501 | High-Resource | Foreign disinformation and general conspiracies outside the 11 narratives. |

---

## 4. Provenance and Source Tracking
Every record in `train.jsonl`, `val.jsonl`, `test.jsonl`, and `gold.jsonl` contains explicit origin metadata:
- `source_name`: EUvsDisinfo, MOROCO, Gazeta, FAKEROM, Audited Seed Benchmark, Moldovan Public Benchmark.
- `source_type`: `debunk`, `news`, `telegram`, `synthetic`.
- `source_url`: Real debunk or source link.
- `url_verified`: True if the URL was confirmed accessible.
- `label_method`: `dataset` or `human`.
- `group_id`: Unique deterministic hash binding translations, paraphrases, and duplicates together.

---

## 5. Known Limitations
1. **Low-Resource Classes (11 & 12)**: Categories 11 (Financial Panic) and 12 (Forced Mobilization) have low sample counts in standard news debunks because they circulate primarily as acute Telegram forward spikes rather than formal press articles. They are marked `LOW-RESOURCE` and handled via prototype retrieval.
2. **Style Shift**: Real Telegram posts feature emoji, channel forward boilerplate, and mixed Romanian/Russian dialects. To bridge this gap, benign Telegram channel feeds and Moldovan gold test posts are included in the evaluation suite.

