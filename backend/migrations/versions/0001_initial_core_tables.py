"""Initial core tables migration: schema_migrations, parameter_sets, users, watchlist_channels."""

REVISION_ID = "0001_initial_core_tables"
DOWN_REVISION: str | None = None

UPGRADE_SQL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        revision TEXT PRIMARY KEY,
        applied_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS parameter_sets (
        version TEXT PRIMARY KEY,
        similarity_threshold REAL NOT NULL,
        time_window_minutes INTEGER NOT NULL,
        collection_interval_minutes INTEGER NOT NULL CHECK (collection_interval_minutes <= 10),
        min_cluster_channels INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        created_by TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        organization TEXT NOT NULL,
        role TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS watchlist_channels (
        id TEXT PRIMARY KEY,
        handle TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        language TEXT NOT NULL,
        status TEXT NOT NULL,
        added_by TEXT NOT NULL,
        added_at TEXT NOT NULL,
        subscribers_count INTEGER NOT NULL DEFAULT 0
    );
    """,
    """
    INSERT OR IGNORE INTO parameter_sets (
        version,
        similarity_threshold,
        time_window_minutes,
        collection_interval_minutes,
        min_cluster_channels,
        created_at,
        created_by
    ) VALUES (
        'v1.4',
        0.82,
        30,
        5,
        3,
        '2026-11-02T12:00:00Z',
        'elena.botnari@scamguard.md'
    );
    """,
)
