"""Database connection and deterministic SQL migration manager."""

import importlib.util
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

MIGRATION_FILE = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "0001_initial_core_tables.py"
)


def _load_initial_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0001", MIGRATION_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load migration module from {MIGRATION_FILE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        migration = _load_initial_migration()
        revision_id = str(migration.REVISION_ID)
        statements: tuple[str, ...] = tuple(migration.UPGRADE_SQL)

        cursor = self._conn.cursor()
        for statement in statements:
            cursor.execute(statement)

        cursor.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (revision, applied_at)
            VALUES (?, ?)
            """,
            (revision_id, datetime.now(UTC).isoformat()),
        )
        self._conn.commit()
        return revision_id

    def get_current_revision(self) -> str:
        self.run_migrations()
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT revision FROM schema_migrations ORDER BY applied_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return str(row["revision"]) if row else "none"


_default_db_manager = DatabaseManager()
_default_db_manager.run_migrations()


def get_database_manager() -> DatabaseManager:
    return _default_db_manager
