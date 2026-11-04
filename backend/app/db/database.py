"""Database connection and deterministic SQL migration manager."""

import importlib.util
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"


def _load_migrations() -> list[ModuleType]:
    modules: list[ModuleType] = []
    for path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load migration module from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    return modules


class DatabaseManager:
    """Manages connections and schema migrations following Single Responsibility Principle."""

    def __init__(self, sqlite_path: str = ":memory:") -> None:
        self._sqlite_path = sqlite_path
        self._conn = sqlite3.connect(sqlite_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    def run_migrations(self) -> str:
        migrations = _load_migrations()
        cursor = self._conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                revision TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
            """
        )
        cursor.execute("SELECT revision FROM schema_migrations")
        applied_revisions = {row[0] for row in cursor.fetchall()}
        latest_revision = "none"

        for index, migration in enumerate(migrations):
            revision_id = str(migration.REVISION_ID)
            if revision_id in applied_revisions:
                latest_revision = revision_id
                continue

            statements: tuple[str, ...] = tuple(migration.UPGRADE_SQL)
            for statement in statements:
                cursor.execute(statement)

            applied_ts = f"2026-11-02T12:00:{index:02d}Z"
            cursor.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (revision, applied_at)
                VALUES (?, ?)
                """,
                (revision_id, applied_ts),
            )
            latest_revision = revision_id

        self._conn.commit()
        return latest_revision

    def get_current_revision(self) -> str:
        self.run_migrations()
        cursor = self._conn.cursor()
        cursor.execute("SELECT revision FROM schema_migrations ORDER BY revision DESC LIMIT 1")
        row = cursor.fetchone()
        return str(row["revision"]) if row else str(datetime.now(UTC))


_default_db_manager = DatabaseManager()
_default_db_manager.run_migrations()


def get_database_manager() -> DatabaseManager:
    return _default_db_manager
