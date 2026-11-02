"""Message storage tables migration: messages, message_texts, message_norm, collection_runs."""

REVISION_ID = "0002_message_storage_tables"
DOWN_REVISION: str | None = "0001_initial_core_tables"

UPGRADE_SQL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        channel_id TEXT NOT NULL,
        telegram_message_id INTEGER NOT NULL,
        posted_at TEXT NOT NULL,
        forwarded_from TEXT,
        view_count INTEGER NOT NULL DEFAULT 0,
        language TEXT NOT NULL DEFAULT 'RO',
        is_deleted_at_source INTEGER NOT NULL DEFAULT 0,
        UNIQUE(channel_id, telegram_message_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS message_texts (
        message_id TEXT PRIMARY KEY,
        raw_text TEXT NOT NULL,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS message_norm (
        message_id TEXT PRIMARY KEY,
        normalised_text TEXT NOT NULL,
        transliterated_text TEXT NOT NULL,
        text_hash TEXT NOT NULL,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS channel_checkpoints (
        channel_id TEXT PRIMARY KEY,
        last_telegram_message_id INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS collection_runs (
        id TEXT PRIMARY KEY,
        started_at TEXT NOT NULL,
        finished_at TEXT NOT NULL,
        status TEXT NOT NULL,
        channels_polled INTEGER NOT NULL DEFAULT 0,
        messages_saved INTEGER NOT NULL DEFAULT 0,
        flood_waits_count INTEGER NOT NULL DEFAULT 0,
        error_message TEXT
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_messages_channel_posted
    ON messages(channel_id, posted_at);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_message_norm_hash
    ON message_norm(text_hash);
    """,
)
