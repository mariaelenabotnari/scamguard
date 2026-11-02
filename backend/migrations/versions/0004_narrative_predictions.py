"""Narrative classification predictions schema migration."""

REVISION_ID = "0004_narrative_predictions"
DOWN_REVISION: str | None = "0003_similarity_and_clusters"

UPGRADE_SQL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS narrative_predictions (
        target_id TEXT PRIMARY KEY,
        target_type TEXT NOT NULL,
        category TEXT NOT NULL,
        confidence REAL NOT NULL,
        matched_claim TEXT NOT NULL,
        model_version TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_narrative_predictions_category
    ON narrative_predictions(category);
    """,
)
