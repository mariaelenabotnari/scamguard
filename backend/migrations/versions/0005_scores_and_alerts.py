"""Channel coordination risk scores and alerts schema migration."""

REVISION_ID = "0005_scores_and_alerts"
DOWN_REVISION: str | None = "0004_narrative_predictions"

UPGRADE_SQL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS channel_scores (
        channel_id TEXT PRIMARY KEY,
        score INTEGER NOT NULL,
        risk_band TEXT NOT NULL,
        cluster_participation_points INTEGER NOT NULL,
        copy_delay_points INTEGER NOT NULL,
        co_movement_points INTEGER NOT NULL,
        narrative_weight_points INTEGER NOT NULL,
        dominant_factor TEXT NOT NULL,
        summary TEXT NOT NULL,
        primary_narrative TEXT NOT NULL,
        parameter_version TEXT NOT NULL,
        computed_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        severity TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'new',
        triggered_at TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        narrative_tag TEXT NOT NULL,
        target_route TEXT NOT NULL,
        parameter_version TEXT NOT NULL
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_alerts_severity_status
    ON alerts(severity, status);
    """,
)
