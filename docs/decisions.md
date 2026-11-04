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
