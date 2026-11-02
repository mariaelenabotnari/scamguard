"""Similarity edges and coordinated clusters schema migration."""

REVISION_ID = "0003_similarity_and_clusters"
DOWN_REVISION: str | None = "0002_message_storage_tables"

UPGRADE_SQL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS similarity_edges (
        id TEXT PRIMARY KEY,
        source_message_id TEXT NOT NULL,
        target_message_id TEXT NOT NULL,
        source_channel_id TEXT NOT NULL,
        target_channel_id TEXT NOT NULL,
        similarity_score REAL NOT NULL,
        match_stage TEXT NOT NULL,
        time_diff_seconds INTEGER NOT NULL,
        parameter_version TEXT NOT NULL,
        UNIQUE(source_message_id, target_message_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS clusters (
        id TEXT PRIMARY KEY,
        headline_summary TEXT NOT NULL,
        narrative_category TEXT NOT NULL,
        channels_count INTEGER NOT NULL,
        messages_count INTEGER NOT NULL,
        window_minutes INTEGER NOT NULL,
        average_similarity REAL NOT NULL,
        first_posted_at TEXT NOT NULL,
        last_posted_at TEXT NOT NULL,
        representative_snippet TEXT NOT NULL,
        parameter_version TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS cluster_messages (
        cluster_id TEXT NOT NULL,
        message_id TEXT NOT NULL,
        channel_id TEXT NOT NULL,
        delay_seconds INTEGER NOT NULL DEFAULT 0,
        similarity_to_centroid REAL NOT NULL DEFAULT 1.0,
        PRIMARY KEY (cluster_id, message_id),
        FOREIGN KEY (cluster_id) REFERENCES clusters(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_clusters_first_posted
    ON clusters(first_posted_at DESC);
    """,
)
