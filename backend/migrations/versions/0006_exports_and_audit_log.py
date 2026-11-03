"""Export quota tracking and observability audit log schema migration."""

REVISION_ID = "0006_exports_and_audit_log"
DOWN_REVISION: str | None = "0005_scores_and_alerts"

UPGRADE_SQL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS export_usage (
        id TEXT PRIMARY KEY,
        actor_key TEXT NOT NULL,
        account_tier TEXT NOT NULL,
        scope TEXT NOT NULL,
        format TEXT NOT NULL,
        rows_exported INTEGER NOT NULL,
        exported_at TEXT NOT NULL
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_export_usage_actor_date
    ON export_usage(actor_key, exported_at);
    """,
    """
    CREATE TABLE IF NOT EXISTS observability_events (
        id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        latency_ms REAL NOT NULL,
        recorded_at TEXT NOT NULL
    );
    """,
)
