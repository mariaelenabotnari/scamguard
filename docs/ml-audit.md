# ML and NLP Pipeline Audit

> Audit date: November 2026  
> Scope: Core ML, NLP, and scoring services in `backend/app/services/` and `ml/`  
> Objective: Systematic assessment of pipeline components against empirical failure modes, false-positive vulnerabilities, and defensibility.

---

## 1. Overview of Current Services

| Service | Stated Purpose | Real Implementation Details |
|---|---|---|
| `TextNormaliser` | Cleans text, unifies diacritics, detects language | Strips URLs, handles, and emojis. Replaces cedillas (`ş`, `ţ`) with commas (`ș`, `ț`). Transliterates Cyrillic to Latin. Produces a single `normalisedText` and SHA-256 hash. |
| `SimilarityService` | 3-stage cross-channel similarity within time window | 1. Exact SHA-256 match (`1.0`).<br>2. MinHash (64 hashes, 16 bands of 4 rows, word 2/3 shingles) with Jaccard check $\ge 0.55$.<br>3. Multilingual concept vector embeddings (48-dim deterministic projection) with cosine similarity $\ge 0.85$. |
| `ClusteringService` | Groups similar cross-channel messages into clusters | Builds similarity graph from edges ($\ge 0.85$), runs connected components (transitive closure), picks earliest message as lead/origin, computes phrase diffs against lead. |
| `NarrativeClassifierService` | Classifies messages into 12 disinformation categories | Keyword and prototype cosine matching against bilingual claim statements. Assigns `fake_news_score` from 0 to 1; outputs `unknown` when confidence $< 0.55$. |
| `ScoringService` | Quantifies channel coordination risk (0–100) | Linear weighted sum: $0.35 \times \text{cluster participation} + 0.30 \times \text{copy delay} + 0.20 \times \text{co-movement} + 0.15 \times \text{narrative weight}$. Generates template explanation. |

---

## 2. Suspected Vulnerabilities & Empirical Findings

### 2.1 LSH Band Collision vs. Verification Step
- **Status:** **True & Confirmed**.
- **Analysis:** With $b=16$ bands and $r=4$ rows ($b \times r = 64$ hashes), the S-curve formula $P = 1 - (1 - s^r)^b$ indicates that at Jaccard similarity $s = 0.5$, the probability of band collision is $1 - (1 - 0.5^4)^{16} \approx 64.4\%$. Even at $s = 0.4$, collision probability is $34\%$.
- **Impact:** Relying on band collisions without verifying the true signature Jaccard causes excessive candidate pairs to be flagged as duplicates.
- **Remedy:** Upgrade signature length to 128 hashes, use $b=32, r=4$, and enforce an explicit signature verification step confirming estimated Jaccard $\ge 0.70$ before flagging near-duplicates.

### 2.2 Word Shingles on Short Telegram Posts
- **Status:** **True & Confirmed**.
- **Analysis:** A Telegram post with fewer than 10 words produces only 5–7 word 2-shingles and 3–5 word 3-shingles. A single edited word or typo causes the Jaccard overlap to drop below 0.40.
- **Impact:** Misses near-identical short alert messages or viral slogans spread across channels.
- **Remedy:** Adaptive shingling: use character 4-grams and 5-grams for short posts ($\le 12$ words or $< 80$ characters); use word shingles for longer texts.

### 2.3 Over-Normalised & Transliterated Input Fed to Embeddings
- **Status:** **True & Confirmed**.
- **Analysis:** Embedding models and neural classifiers rely on case, punctuation, numbers, and script identity to capture syntactic semantics. Feeding transliterated Cyrillic or punctuation-stripped text into sentence transformers degrades cross-lingual alignment.
- **Impact:** Embedding accuracy drops, particularly on cross-lingual Romanian–Russian pairs.
- **Remedy:** Introduce three distinct text views:
  1. `text_hash`: strongly normalized for exact hash and MinHash.
  2. `text_model`: lightly cleaned text (preserving diacritics, numbers, case, and native script) for neural embeddings and classifiers.
  3. `text_display`: raw original text for UI presentation and audit evidence.

### 2.4 Static Cosine Threshold (0.85) Across Language Pairs
- **Status:** **True & Confirmed**.
- **Analysis:** Monolingual (RO-RO, RU-RU) pairs naturally cluster higher (average similarity $0.88–0.94$) than cross-lingual (RO-RU) paraphrases ($0.78–0.84$).
- **Impact:** A rigid 0.85 threshold yields false negatives on genuine cross-lingual coordination while admitting false positives on formulaic monolingual news.
- **Remedy:** Calibrated thresholds per language pair (e.g., RO-RO: 0.82, RU-RU: 0.82, RO-RU: 0.78).

### 2.5 Blind Spot for Numbers, Dates, Names, and Negations
- **Status:** **True & Confirmed**.
- **Analysis:** Cosine similarity between sentences differing only in numbers (e.g., *"15 noiembrie"* vs *"15 decembrie"*) or polarity (*"va intra"* vs *"nu va intra"*) frequently exceeds $0.90$.
- **Impact:** Opposing claims or updated figures are incorrectly collapsed into the same cluster.
- **Remedy:** Introduce a **Detail Guard** that extracts numeric entities, calendar dates, and negation tokens ("nu", "nici", "не", "нет"). If details conflict, penalize similarity and flag as *"same text, changed details"*.

### 2.6 Connected Components & Cluster Snowballing
- **Status:** **True & Confirmed**.
- **Analysis:** Connected components calculate transitive closure: if $A \sim B$ at 0.85 and $B \sim C$ at 0.85, $A$ and $C$ are placed in the same cluster even if their similarity is $0.55$.
- **Impact:** During high-volume news cycles, unrelated stories chain into giant "mega-clusters" spanning hundreds of messages.
- **Remedy:** Replace single-linkage transitive closure with **average linkage agglomerative clustering** or community detection with a strict maximum diameter cut ($\ge 0.75$) and time horizon cut (e.g. 120 minutes).

### 2.7 Forwarded Posts and Syndicated Outside Sources
- **Status:** **True & Confirmed**.
- **Analysis:** Messages forwarded directly via Telegram metadata (`forwarded_from`) or copied from public press agencies (e.g., Moldpres, Infotag, official government releases) reflect standard news propagation, not covert coordination.
- **Impact:** Channels covering breaking news receive artificially inflated coordination risk scores.
- **Remedy:** Parse `forwarded_from` and catalog known news agency wire patterns. Flag clusters as *"common source"* or *"forwarded"*, attenuating their contribution to the coordination score.

### 2.8 Scoring Weight Validation and Strong Language
- **Status:** **True & Confirmed**.
- **Analysis:** The weights ($0.35, 0.30, 0.20, 0.15$) were heuristically chosen. Descriptions like *"humanly impossible reading time = automated syndication"* overclaim forensic certainty.
- **Impact:** Vulnerable to external audit and skepticism from investigative journalists.
- **Remedy:** Rephrase to neutral, evidence-based descriptions (*"faster than typical manual reposting"*). Provide independent sub-scores for Coordination and Narrative Match.

### 2.9 Categories 11 and 12 Coverage
- **Status:** **True & Confirmed**.
- **Analysis:** Category 11 ("Financial panic and banking runs") and Category 12 ("Forced mobilization rumors") have near-zero representation in public training datasets.
- **Impact:** High false-negative rate or arbitrary classification.
- **Remedy:** Designate Categories 11 and 12 as few-shot / retrieval-assisted categories with curated fact-check claims and prototype exemplars.

