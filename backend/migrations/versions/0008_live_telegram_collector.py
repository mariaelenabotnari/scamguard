"""Live Telegram collector schema migration: channels, messages, edits, boilerplates."""

REVISION_ID = "0008_live_telegram_collector"
DOWN_REVISION: str | None = "0007_user_verification_and_username"

UPGRADE_SQL: tuple[str, ...] = (
    """
    ALTER TABLE watchlist_channels ADD COLUMN telegram_channel_id INTEGER;
    """,
    """
    ALTER TABLE watchlist_channels ADD COLUMN last_collected_at TEXT;
    """,
    """
    ALTER TABLE watchlist_channels ADD COLUMN last_error TEXT;
    """,
    """
    ALTER TABLE messages ADD COLUMN has_media INTEGER NOT NULL DEFAULT 0;
    """,
    """
    ALTER TABLE messages ADD COLUMN media_type TEXT;
    """,
    """
    ALTER TABLE messages ADD COLUMN forwards INTEGER NOT NULL DEFAULT 0;
    """,
    """
    ALTER TABLE messages ADD COLUMN edit_date TEXT;
    """,
    """
    ALTER TABLE messages ADD COLUMN grouped_id TEXT;
    """,
    """
    ALTER TABLE messages ADD COLUMN is_forward INTEGER NOT NULL DEFAULT 0;
    """,
    """
    ALTER TABLE messages ADD COLUMN forward_source_channel_id TEXT;
    """,
    """
    ALTER TABLE messages ADD COLUMN forward_source_name TEXT;
    """,
    """
    ALTER TABLE messages ADD COLUMN forward_source_date TEXT;
    """,
    """
    ALTER TABLE messages ADD COLUMN reply_to_id INTEGER;
    """,
    """
    ALTER TABLE messages ADD COLUMN post_link TEXT;
    """,
    """
    ALTER TABLE messages ADD COLUMN first_seen_at TEXT;
    """,
    """
    ALTER TABLE messages ADD COLUMN last_seen_at TEXT;
    """,
    """
    ALTER TABLE messages ADD COLUMN deleted_at TEXT;
    """,
    """
    ALTER TABLE messages ADD COLUMN skip_similarity INTEGER NOT NULL DEFAULT 0;
    """,
    """
    ALTER TABLE collection_runs ADD COLUMN channel_id TEXT;
    """,
    """
    CREATE TABLE IF NOT EXISTS message_edits (
        id TEXT PRIMARY KEY,
        message_id TEXT NOT NULL,
        old_raw_text TEXT NOT NULL,
        new_raw_text TEXT NOT NULL,
        edited_at TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS channel_boilerplates (
        channel_id TEXT NOT NULL,
        boilerplate_text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (channel_id, boilerplate_text)
    );
    """,
)
