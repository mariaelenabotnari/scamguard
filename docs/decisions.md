# Machine Learning & NLP Architecture Decisions

> Project: ScamGuard / ChorusWatch  
> Date: November 2026  
> Context: Upgrade of Telegram Coordination Detection & Disinformation Narrative Pipeline

---

## Decision 1: Taxonomy Management & Low-Resource Categories (11 & 12)
- **Problem:** Categories 11 ("Financial panic, bank runs and currency devaluation") and 12 ("Forced mobilization and border militarization") are critical crisis-period disinforming narratives in Moldova, but have near-zero representation in standard public NLP benchmarks.
- **Decision:** Rather than dropping these categories or arbitrarily merging them into generic economic or political buckets, we establish a **Hybrid Retrieval-Prototype Architecture**:
  1. Hand-curated bilingual claim exemplars from local fact-checking initiatives (StopFals.md and EUvsDisinfo) are indexed in `ml/data/curated/moldova_debunk_claims.jsonl`.
  2. Inference combines token-overlap keywords with semantic prototype embeddings against the curated debunk repository.
  3. Matches to Categories 11 and 12 link directly to the verified debunk URL as tangible evidence.

---

## Decision 2: Elimination of the "Fake News Score" in Favor of Narrative Match Likelihood
- **Problem:** The original pipeline produced a scalar `fake_news_score` from 0.0 to 1.0. Labeling a single short, noisy Telegram post as definitively "fake" using an automated text model is scientifically indefensible, prone to domain-shift errors, and creates legal/editorial liability for journalists.
- **Decision:**
  1. The term "fake news score" is completely deprecated across the backend and UI.
  2. It is replaced by **Narrative Match Likelihood** (`narrative_match_confidence`), which measures semantic alignment with documented disinformation narratives, and a boolean flag `matches_known_narrative`.
  3. The platform strictly claims: *"Message matches known disinformation narrative [X] with confidence [Y%]"*, accompanied by the nearest verified debunk citation. It never claims to determine truth or falsehood in isolation.

---

## Decision 3: Decoupling Risk Scoring into Two Independent Axes
- **Problem:** The v1 scoring formula collapsed coordination speed, cluster volume, and narrative content into a single monolithic number ($0.35 \times \text{cluster} + 0.30 \times \text{delay} + 0.20 \times \text{co-movement} + 0.15 \times \text{narrative}$). This obfuscated whether a channel was flagged for behavioral automation or for editorial topic choice.
- **Decision:**
  1. Scoring v2 outputs two distinct visible metrics:
     - **Coordination Score (0–100):** Pure behavioral signal derived from cascade participation rate, rapid reposting velocity (< 15 min), and co-movement repetition.
     - **Narrative Risk Level (None / Low / Medium / High):** Content signal based on verified narrative category match and fact-check citations.
  2. **Activity Rate Normalization:** Channels with 5,000 posts vs. 20 posts are evaluated on normalized coordination rates, with empirical shrinkage for low-volume accounts (< 3 posts = "not enough data").
  3. **Attenuating Legitimate Propagation:** Explicit Telegram forwards and acknowledged news wire agencies (e.g., Moldpres, Infotag) are attenuated so legitimate press syndication is not mislabeled as covert coordination.

---

## Decision 4: Neutral, Defensible Forensic Wording
- **Problem:** Phrases such as *"humanly impossible reading time = automated syndication"* overclaim certainty about human cognition and technical intent.
- **Decision:** All score explanations are standardized on neutral, evidence-based descriptions:
  - *"Represents reposting significantly faster than typical manual editorial lag (< 5 minutes across channels)."*
  - *"Observed in N coordinated cascades alongside co-occurring channels."*

---

## Decision 5: Channel Coordination Groups
- **Problem:** Investigators need to understand the network topology: which channels repeatedly act together across multiple cascades?
- **Decision:** Construct an undirected weighted channel co-posting graph where edge weights reflect shared cascade count and posting proximity. Apply community detection with a minimum threshold of $\ge 3$ shared cascades to identify stable coordination groups.

---

## Decision 6: Unification of the Channel Risk Scoring Formula
- **Problem:** Two competing scoring formulations appeared across earlier drafts and implementations:
  1. A composite two-axis formula: $\text{Final} = 0.60 \times \text{Coordination} + 0.40 \times \text{Narrative}$.
  2. A 4-factor breakdown (35% cluster participation, 30% copy delay, 20% co-movement, and 15% narrative weight).
  Under the second formulation, narrative severity was counted once inside the coordination score, and then again when combining coordination with narrative risk, leading to narrative double-counting.
- **Decision:**
  1. Keep **pure behavioral factors** inside the Coordination Score (0–100):
     - **Cluster Participation Share ($w_1 = 0.40$):** Frequency of participating in multi-channel coordinated cascades.
     - **Copy Delay / Velocity ($w_2 = 0.35$):** Reposting velocity relative to anchor ($< 5$ minutes indicating automated/scripted syndication).
     - **Co-Movement Repetition ($w_3 = 0.25$):** Recurrent temporal co-occurrence alongside the same peer channels.
     *(Sum of behavioral weights = 1.00; narrative is completely removed from this calculation).*
  2. Maintain **Narrative Severity** as an independent content axis (0–100): None (0), Low (25), Medium (60), High (90).
  3. Compute the **Overall Channel Risk Score**:
     $$\text{Overall Risk Score} = 0.60 \times \text{Coordination Score} + 0.40 \times \text{Narrative Score}$$
  4. Both numbers and their factor weights are versioned in `system_parameters`.

---

## Decision 7: Production Multi-Tier Similarity Pipeline
- **Problem:** Legacy project notes described a pipeline using SHA-256 + MinHash/LSH + embeddings, while the production code executes Token Jaccard + Character 3-gram Cosine + Multilingual Embeddings. This discrepancy created confusion about what actually runs in inference.
- **Decision:** Explicitly document and standardize the exact 4-tier similarity pipeline executed in production:
  1. **Pre-Processing & Normalisation:** Multi-view text normalization (homoglyph substitution, diacritic stripping, channel signature/boilerplate removal, lowercasing).
  2. **Tier 1 (Exact Match):** Cryptographic SHA-256 hash comparison on normalized text. Exact hash matches immediately return a similarity score of $1.0$.
  3. **Tier 2 (Lexical Surface Similarity):** Weighted combination of Token Jaccard and Character 3-Gram Cosine:
     $$\text{Lexical Score} = 0.40 \times \text{Jaccard}_{\text{tokens}} + 0.60 \times \text{Cosine}_{\text{char-3grams}}$$
     Candidate pairs exceeding the threshold ($\ge 0.75$) form lexical candidate edges.
  4. **Tier 3 (Semantic Paraphrase & Cross-Language):** Multilingual vector embedding cosine similarity using CPU-friendly multilingual embeddings. Pairs exceeding threshold ($\ge 0.80$) are captured as semantic variant edges (supporting Romanian $\leftrightarrow$ Russian translations and heavy paraphrasing).
  5. Pairs falling below both Tier 2 and Tier 3 thresholds are pruned before clustering.

---

## Decision 8: Transparent Classifier Designation ("Rule-Based Narrative Match")
- **Problem:** Describing the narrative classifier as an "AI/ML narrative detector" overclaims capability and creates unrealistic expectations that an end-to-end deep neural network is making unsupervised editorial determinations.
- **Decision:**
  1. Explicitly designate the classifier in documentation, API payloads, and UI badges as a **"Rule-Based Narrative Match"** engine.
  2. The mechanism combines:
     - Curated bilingual keyword stems (Romanian and Russian) across 12 civic crisis categories.
     - Prototype claim cosine similarity against verified debunk repositories from **StopFals.md** and **EUvsDisinfo**.
  3. Fine-tuned transformer models will only be integrated when trained on labeled pilot datasets with proven ground-truth benchmarks.

