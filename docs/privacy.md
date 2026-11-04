# ScamGuard Data Privacy and Retention Policy

## 1. Principles
ScamGuard monitors public Telegram broadcast channels to detect coordinated disinformation campaigns in the Republic of Moldova. It adheres strictly to data minimization and transparency principles:

1. **Public Information Only**: Only public broadcast channels are monitored. Private groups, user-to-user chats, and personal accounts are strictly rejected.
2. **Data Minimization**: Raw message text is decoupled from normalized investigative evidence (normalized text representations, character 3-gram hashes, token n-grams, and vector embeddings).
3. **No Profiling**: ScamGuard tracks channels and messages, never individual private citizens.

## 2. Retention Schedule
- **Raw Message Text**: Retained in the database for **90 days** from initial collection for investigative review and manual verification.
- **Automated Text Purging (Day 91+)**: After 90 days, raw message text is permanently purged from `message_texts`. Only normalized text snippets, cryptographic hashes (SHA-256), and statistical counts (views, forwards) are retained for cluster timeline reconstruction and longitudinal reporting.
- **Deleted at Source (Immediate Purge)**: If a post is removed or deleted on Telegram, the deletion check job immediately deletes `raw_text` from `message_texts`, records `deleted_at`, flags the post as `is_deleted_at_source = 1`, and retains only the normalized snippet and hash.

## 3. Data Flow and Access Control
- All stored messages and analysis results are accessible exclusively through authenticated endpoints.
- Role-based access control enforces access tiers (Admin, Journalist, Viewer).
