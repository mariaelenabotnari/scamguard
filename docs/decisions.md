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

## Decision 5: Channel Coordination Groups (FR-06)
- **Problem:** Investigators need to understand the network topology: which channels repeatedly act together across multiple cascades?
- **Decision:** Construct an undirected weighted channel co-posting graph where edge weights reflect shared cascade count and posting proximity. Apply community detection with a minimum threshold of $\ge 3$ shared cascades to identify stable coordination groups.

