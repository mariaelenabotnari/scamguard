# ScamGuard Data Flow Audit & Live Data Roadmap

> Branch: `chore/data-flow-audit`  
> Date: November 2026  
> Purpose: Comprehensive map of every screen, widget, API client, backend endpoint, service, and database table. Identifies all mock fixtures and fixed backend values, serving as the master to-do list for end-to-end live Telegram data integration.

---

## 1. Master Data Flow Table

| Screen / View | Widget / Component | Frontend API Function | Backend Endpoint | Backend Service | Database Table(s) | Current State | Required Action for Live Mode |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Overview** (`/overview`, `/`) | Greeting Banner | `DashboardService.getOverview` | `GET /api/v1/dashboard/overview` | `DashboardService` | `watchlist_channels`, `system_parameters` | **Fixed Backend Values** (fallback counts 312, 48) | Query `COUNT(*)` from `watchlist_channels` and active `clusters` dynamically |
| **Overview** (`/overview`, `/`) | 4 KPI Stat Cards | `DashboardService.getOverview` | `GET /api/v1/dashboard/overview` | `DashboardService` | `watchlist_channels`, `messages`, `clusters`, `alerts` | **Frontend Mock / Fixed Backend** (reads `MOCK_DASHBOARD_OVERVIEW_BY_RANGE` or fixed values) | Compute real metrics from `messages` (range), `clusters`, `alerts` |
| **Overview** (`/overview`, `/`) | Activity Timeline Chart | `DashboardService.getOverview` | `GET /api/v1/dashboard/overview` | `DashboardService` | `messages`, `clusters` | **Fixed Backend Presets** (`_TIMELINE_PRESETS` in `dashboard_service.py`) | Run SQL time-bucket aggregations on `messages.posted_at` and `clusters.first_posted_at` (24h/7d/30d) |
| **Overview** (`/overview`, `/`) | Top Coordinated Clusters | `DashboardService.getOverview` | `GET /api/v1/dashboard/overview` | `DashboardService` | `clusters`, `cluster_messages` | **Frontend Mock / Seed Array** | Query top $N$ recent clusters ordered by `channels_count DESC, average_similarity DESC` |
| **Overview** (`/overview`, `/`) | Riskiest Channels List | `DashboardService.getOverview` | `GET /api/v1/dashboard/overview` | `DashboardService` | `channel_scores`, `watchlist_channels` | **Frontend Mock / Seed Array** | Query `channel_scores` ordered by `score DESC` join `watchlist_channels` |
| **Overview** (`/overview`, `/`) | Narrative Distribution | `DashboardService.getOverview` | `GET /api/v1/dashboard/overview` | `DashboardService` | `clusters`, `narrative_predictions` | **Frontend Mock / Fixed Counts** | Group clusters by `narrative_category` over active sliding window |
| **Overview** (`/overview`, `/`) | System Status Bar | `DashboardService.getOverview` | `GET /api/v1/dashboard/overview` | `DashboardService` | `collection_runs`, `channel_checkpoints` | **Hardcoded Frontend Mock** (`systemStatus` in mock) | Query latest run from `collection_runs` and checkpoint freshness |
| **Overview** (`/overview`, `/`) | Coordination Groups | `DashboardService.getOverview` | `GET /api/v1/scoring/coordination-groups` | `ScoringService` | `cluster_messages`, `similarity_edges` | **Hardcoded Seed Graph** | Build dynamic co-occurrence graph from shared `cluster_messages` |
| **Watchlist** (`/channels`) | Channels Table | `ChannelService.getWatchlist` | `GET /api/v1/watchlist` | `WatchlistService` | `watchlist_channels`, `channel_scores` | **Frontend Mock** (`MOCK_WATCHLIST_CHANNELS`) | Call `GET /api/v1/watchlist?page=1&pageSize=300` backed by SQLite/Postgres |
| **Watchlist** (`/channels`) | Add Channel Form | `ChannelService.addWatchlistChannel` | `POST /api/v1/watchlist` | `WatchlistService`, `TelegramCollectorService` | `watchlist_channels`, `channel_checkpoints` | **Frontend Mock Store** | Call `POST /api/v1/watchlist`, resolve Telegram handle via MTProto, start backfill |
| **Watchlist** (`/channels`) | Toggle Active/Pause | `ChannelService.toggleWatchlistStatus` | `PATCH /api/v1/watchlist/{id}` | `WatchlistService` | `watchlist_channels` | **Frontend Mock Store** | Update `status = 'active'/'paused'` in database |
| **Watchlist** (`/channels`) | Remove Channel | `ChannelService.removeWatchlistChannel` | `DELETE /api/v1/watchlist/{id}` | `WatchlistService` | `watchlist_channels` | **Frontend Mock Store** | Delete or soft-delete from `watchlist_channels` |
| **Channel Detail** (`/channels/:id`) | Profile Header & Risk Band | `ChannelService.getChannelDetail` | `GET /api/v1/channels/{id}` | `ScoringService` | `watchlist_channels`, `channel_scores` | **Frontend Mock** (`MOCK_CHANNEL_DETAILS`) | Call backend `GET /api/v1/channels/{id}` with live DB profile |
| **Channel Detail** (`/channels/:id`) | Score Factors Breakdown | `ChannelService.getChannelDetail` | `GET /api/v1/channels/{id}` | `ScoringService` | `channel_scores` | **Frontend Mock / Seed Profiles** | Return computed factors (`clusterParticipation`, `copyDelay`, `coMovement`, `narrativeRisk`) |
| **Channel Detail** (`/channels/:id`) | Score History Sparkline | `ChannelService.getChannelDetail` | `GET /api/v1/channels/{id}` | `ScoringService` | `channel_score_history` | **Static Mock Array** | Query historical scores from analysis runs |
| **Channel Detail** (`/channels/:id`) | "Often Posts Together With" | `ChannelService.getChannelDetail` | `GET /api/v1/channels/{id}` | `ScoringService` | `cluster_messages` | **Static Seed List** | Query channels that co-occur in $\ge 2$ shared clusters |
| **Channel Detail** (`/channels/:id`) | Linked Clusters Table | `ChannelService.getChannelDetail` | `GET /api/v1/channels/{id}` | `ScoringService` | `cluster_messages`, `clusters` | **Static Seed List** | Join `cluster_messages` on `clusters` for `channel_id` |
| **Clusters List** (`/clusters`) | Clusters Table & Filter | `ClusterService.getClusters` | `GET /api/v1/clusters` | `ClusteringService` | `clusters`, `cluster_messages` | **Frontend Mock** (`MOCK_CLUSTERS`) | Query live `clusters` table with category & query filter |
| **Clusters List** (`/clusters`) | Run Cluster Detection | `(Admin trigger)` | `POST /api/v1/clusters/detect` | `ClusteringService` | `messages`, `similarity_edges`, `clusters` | **Functional Backend** | Trigger dynamic sliding window clustering over unclustered posts |
| **Cluster Detail** (`/clusters/:id`) | Summary Header | `ClusterService.getClusterDetail` | `GET /api/v1/clusters/{id}` | `ClusteringService` | `clusters` | **Frontend Mock** (`DEFAULT_CLUSTER_DETAIL`) | Fetch cluster record by ID from `clusters` table |
| **Cluster Detail** (`/clusters/:id`) | Interactive Timeline | `ClusterService.getClusterDetail` | `GET /api/v1/clusters/{id}` | `ClusteringService` | `cluster_messages`, `messages` | **Frontend Mock** (`timeline` in `cluster.mock.ts`) | Dynamic calculation: $t_{\text{anchor}} = \min(\text{posted\_at})$, $\Delta t_i = t_i - t_{\text{anchor}}$ |
| **Cluster Detail** (`/clusters/:id`) | Message Comparison & Diffs | `ClusterService.getClusterDetail` | `GET /api/v1/clusters/{id}` | `ClusteringService`, `SimilarityService` | `messages`, `message_texts`, `message_norm` | **Frontend Mock** (`diffTokens` in `cluster.mock.ts`) | Compute LCS token diff against anchor message dynamically |
| **Cluster Detail** (`/clusters/:id`) | Deleted Post Handling | `ClusterService.getClusterDetail` | `GET /api/v1/clusters/{id}` | `TelegramCollectorService` | `messages`, `message_norm` | **Frontend Mock** (hardcoded `isDeletedAtSource: true`) | Read `messages.is_deleted_at_source`, show normalized copy with preserved hash |
| **Risk Ranking** (`/ranking`) | Leaderboard Table | `RankingService.getRankings` | `GET /api/v1/channels/ranking` | `ScoringService` | `channel_scores`, `watchlist_channels` | **Frontend Mock** (`MOCK_RANKED_CHANNELS`) | Fetch ordered channels by `score DESC` from `channel_scores` |
| **Risk Ranking** (`/ranking`) | Score Explanation Modal | `RankingService.getRankings` | `GET /api/v1/channels/ranking` | `ScoringService` | `channel_scores` | **Frontend Mock Explanation** | Return audit-ready explanation sentence + dominant factor |
| **Search** (`/search`) | Unified Search | `SearchService.searchAll` | `GET /api/v1/search` | `SearchService` | `watchlist_channels`, `message_texts`, `clusters` | **Frontend Mock** (`search.mock.ts`) | Execute SQL `LIKE` / FTS across channels, messages, and clusters |
| **Alerts** (`/alerts`) | Alerts Queue | `AlertService.getAlerts` | `GET /api/v1/alerts` | `AlertService` | `alerts` | **Frontend Mock** (`MOCK_ALERTS`) | Fetch non-dismissed alerts from `alerts` table |
| **Alerts** (`/alerts`) | Dismiss Alert | `AlertService.dismissAlert` | `POST /api/v1/alerts/{id}/dismiss` | `AlertService` | `alerts` | **Frontend Mock State** | Update `status = 'dismissed'` in database |
| **Settings** (`/admin`) | Parameters Form | `AdminService.getParameters` | `GET /api/v1/admin/parameters` | `AdminService` | `system_parameters` | **Functional Backend** | Read latest versioned parameters row |
| **Settings** (`/admin`) | Save Parameters | `AdminService.updateParameters` | `POST /api/v1/admin/parameters` | `AdminService` | `system_parameters` | **Functional Backend** | Insert new version row (`v1.4` $\to$ `v1.5`) |
| **Auth** (`/register`, `/login`) | Self-Registration & Verify | `AuthService.register`, `verifyEmail` | `POST /api/v1/auth/register`, `/verify-email` | `AuthService`, `EmailService` | `users`, `user_profiles`, `email_verification_codes` | **Fully Live Backend** | Connected to database with real JWT session |

---

## 2. To-Do List by Pipeline Phase

### Phase 1: Telegram Ingestion (`feat/be-telegram-collector-live`)
- [ ] Connect real Telethon MTProto client (`TelegramCollectorService`) using `TELEGRAM_API_ID` & `TELEGRAM_API_HASH`.
- [ ] Resolve channel handles/URLs to numerical `telegram_channel_id`, title, and subscriber count.
- [ ] Implement historical backfill for $N$ days (default: 7) in rate-limited batches.
- [ ] Implement incremental collection with `min_id = last_message_id`.
- [ ] Handle Telegram post realities: albums (group caption), forward attribution, deleted post text purging, boilerplate signature removal.
- [ ] Enforce `FloodWaitError` backoff and record metrics in `collection_runs`.

### Phase 2: Analysis Pipeline Orchestration (`feat/be-analysis-pipeline`)
- [ ] Create an automated job running after collection: `new/edited messages` $\to$ `normalise` $\to$ `similarity` $\to$ `clustering` $\to$ `narrative classify` $\to$ `scoring` $\to$ `alerts`.
- [ ] Make pipeline runs idempotent: re-running on identical data preserves existing cluster IDs and scores.
- [ ] Store parameters and model version with every run in `analysis_runs`.

### Phase 3: Dynamic Timeline & Diffs (`feat/be-timeline-real`)
- [ ] Compute cluster anchor $t_0$ as $\min(\text{posted\_at})$ and delays $\Delta t = t_i - t_0$ in seconds from stored UTC timestamps.
- [ ] Compute token-level LCS diffs comparing variant posts to the anchor message.
- [ ] Generate real time-series aggregations for Overview charts (`24h`, `7d`, `30d`).

### Phase 4: Live API Endpoints (`feat/be-api-live`)
- [ ] Update `DashboardService` to aggregate from real `messages`, `clusters`, and `channel_scores` instead of `_TIMELINE_PRESETS` and fixed integers.
- [ ] Ensure all pagination, counts, and reason texts are consistent across endpoints.

### Phase 5: Frontend Integration (`feat/int-live-*`)
- [ ] Switch frontend services to call real backend endpoints when `VITE_USE_MOCKS=false`.
- [ ] Add loading, empty, and error states across all pages.
- [ ] Render a visible "Demo data" indicator if records originate from `is_demo = true` seed fixtures.

### Phase 6: Database Demo Seed (`feat/be-demo-seed`)
- [ ] Implement CLI command `python -m app.cli seed-demo` that populates the real database tables (`messages`, `watchlist_channels`) with realistic Romanian and Russian test campaigns marked `is_demo = true`, then runs the real analysis pipeline on them.
