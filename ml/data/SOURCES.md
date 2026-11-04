# ScamGuard Narrative Classification — Dataset Sources & Licences

> **Important Data Boundary Rule:**
> All raw source files (`ml/data/raw/*`), processed partition files (`ml/data/processed/*`), and model artifacts (`ml/models/*`) are strictly excluded via `.gitignore` and must never be committed to git.

---

## 1. Inventory of Vetted Sources

| Source Name | Modality & Domain | Languages | Row Count | Licence | Origin / Reference | Role in ScamGuard |
|---|---|---|---|---|---|---|
| **EUvsDisinfo Database** | Fact-checked claims & debunks | Russian, Romanian, English | 9,075 | CC BY-SA 4.0 | Kaggle `imuhammad/euvsdisinfo-disinformation-database` & Zenodo `10514307` | Primary disinformation claims and debunk summaries across Categories 1–9, 11–13. |
| **MOROCO (Moldavian & Romanian Dialectal Corpus)** | News articles (culture, finance, politics, sports, tech, science) | Romanian & Moldavian dialect | 33,564 | CC BY-NC-SA 4.0 | Butnaru & Ionescu (2019), GitHub `butnaruandrei/MOROCO` | Benign baseline (Category 10) for Moldovan journalistic language and phrasing. |
| **FAKEROM Benchmark** | News articles (real vs. fake) | Romanian | 2,196 | Open Academic | Hugging Face `mihalca/Fakerom_updated_original` | Romanian fake news and verified real news baseline. |
| **Gazeta (RU) News Corpus** | News articles (culture, economics, sports, science) | Russian | 1,500 | Open / Fair Use | Hugging Face `IlyaGusev/gazeta` | Benign Russian text baseline (Category 10) to balance Russian language representation. |
| **Moldovan Telegram Public Stream** | Public channel messages | Romanian & Russian | 200+ | Public Broadcast | ScamGuard MTProto Collector | Evaluation benchmarks, Telegram noise injection, and independent gold set. |

---

## 2. Integrity and Provenance Guarantees
1. **Honest Attribution**: Every record specifies its exact `source_name`, `source_type` (`debunk`, `news`, `telegram`, `synthetic`), and verified upstream URL.
2. **No Invented Citations**: Fictitious URLs and unverified synthetic entries are strictly forbidden in benchmark evaluations.
3. **Data Leakage Safeguard**: Cross-lingual grouping (`group_id`) ensures that no claim or its translations/paraphrases cross the boundary between training and evaluation splits.
