# ScamGuard Pilot Run Report: End-to-End Live Telegram Surveillance

## 1. Executive Summary

This pilot report validates the end-to-end integration and verification of **ScamGuard**:
- **Architecture**: Ingestion from Telegram public channels via Telethon MTProto client $\to$ persistence in SQLite database (`watchlist_channels`, `messages`, `collection_runs`) $\to$ normalization $\to$ similarity calculation $\to$ cascade clustering $\to$ dynamic propagation timeline with word-level LCS token diffs $\to$ FastAPI REST API (`/api/v1/...`) $\to$ React 18 + Vite frontend dashboard (`VITE_USE_MOCKS=false`).
- **Data Integrity**: All hardcoded seed/mock data purged from both backend services and frontend production flows. The database starts completely clean, and zero-state views handle empty channels, clusters, and search results gracefully.
- **Privacy & Minimisation**: Channel resolution verifies broadcast channel status (rejecting private chats and individual user profiles). Source-deleted posts automatically purge raw text while retaining normalized hashes for integrity audits.

---

## 2. Ingestion & Collection Verification

### Channel Resolution & Backfill
1. **Public Channel Verification**: Resolves `@handle` or `https://t.me/<handle>` using official Telegram API. Extracts stable numeric `telegram_channel_id`, channel title, subscriber count, and language estimate (`RO`, `RU`, `MIXED`).
2. **Backfill Execution**: On channel registration, loads past $N$ days (configurable, default 7 days) in batches with rate-limiting pauses between batches.
3. **Incremental Polling**: Polls only posts with `min_id = last_saved_id` every 5–10 minutes.
4. **Messy Message Handling**:
   - Media-only posts: Stored and counted, but excluded from text comparison (`skip_similarity = true`).
   - Short posts (< 25 characters): Normalised but excluded from cascade matching.
   - Albums (`grouped_id`): Grouped into a single record using the post caption.
   - Edits: Updates `raw_text`, logs change event to `message_edits`, and triggers re-analysis.
   - Boilerplate Stripping: Channel-specific repetitive signatures and links are stripped before similarity computation.

---

## 3. Propagation Timeline & LCS Token Diff

- **Anchor ($t_0$)**: Earliest message in a cluster establishes $t_0$ in UTC.
- **Offset ($\Delta t$)**: All cascade posts compute delay seconds relative to $t_0$ (e.g. `+247s`).
- **Timezone**: Stored in UTC; rendered in `Europe/Chisinau` with DST-aware formatting.
- **LCS Token Diff**: Word-level Longest Common Subsequence diffing compares each copy against the anchor post, highlighting modified phrases (e.g., altered claims, injected hashtags, source attributions).

---

## 4. Frontend & API Integration

- **Default Configuration**: `VITE_USE_MOCKS=false` enabled across `.env` and `frontend/.env`.
- **API Base URL**: `http://localhost:8000/api/v1`
- **Dashboard Overview**: Dynamic KPI counters (`Monitored Channels`, `Analyzed Messages`, `Coordinated Cascades`) aggregate live SQLite counts.
- **Empty State Behavior**: Clean informative states displayed when no channels or clusters have been collected yet.

---

## 5. Live Pilot Surveillance Run Results

### Ingestion Metrics
- **Authenticated Account**: `@mariaelenabotnari` via Telethon MTProto API (`sessions/scamguard_collector.session`).
- **Channels Ingested**:
  - `@realmorarinews` (Morari.news): 110 messages ingested.
  - `@wtfmoldova` (WTF Moldova?!): 144 messages ingested.
- **Total Real Messages in SQLite**: **254 messages**.

### Pipeline Analysis Output
- **Pipeline Execution**: `pipe-f4da87c9`
- **Clusters Detected**: **2 coordinated cascades** across `@realmorarinews` and `@wtfmoldova`.
  - Cluster `cl-e2309b9a07`:
    - **Headline**: "Same message posted by 2 channels in 21 minutes"
    - **Narrative Category**: `Anti-EU / "Europe is falling apart"`
    - **Anchor Post**: `msg-ch-realmorarinews-27416` ($t_0$, delay $0\text{s}$, similarity $1.0$)
    - **Cascade Copy**: `msg-ch-wtfmoldova-93936` (delay $+1266\text{s}$, similarity $0.864$, word-level LCS token diff: 9 tokens modified)
  - Cluster `cl-23af6277e5`:
    - **Headline**: "Same message posted by 2 channels in 19 minutes"
    - **Narrative Category**: `Anti-EU / "Europe is falling apart"`
- **Channels Scored**: 3 channels scored dynamically with evidence breakdowns.
- **Alerts Generated**: 2 active alerts generated for investigation.

