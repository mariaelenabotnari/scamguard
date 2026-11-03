"""User verification codes and username column schema migration."""

REVISION_ID = "0007_user_verification_and_username"
DOWN_REVISION: str | None = "0006_exports_and_audit_log"

UPGRADE_SQL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS email_verification_codes (
        email TEXT PRIMARY KEY,
        code TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id TEXT PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        is_verified INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """,
)

