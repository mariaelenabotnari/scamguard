"""User and system parameter repositories backed by SQLite/PostgreSQL."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, cast

from app.core.security import PasswordHasher
from app.db.database import DatabaseManager
from app.dtos.auth_dto import SystemParametersDto, UserRole


@dataclass(frozen=True)
class StoredUserRecord:
    id: str
    email: str
    full_name: str
    organization: str
    role: UserRole
    password_hash: str
    created_at: str
    username: str = ""
    is_verified: bool = True


class IUserRepository(Protocol):
    def get_by_email(self, email: str) -> StoredUserRecord | None: ...
    def get_by_username(self, username: str) -> StoredUserRecord | None: ...
    def get_by_identifier(self, identifier: str) -> StoredUserRecord | None: ...
    def get_by_id(self, user_id: str) -> StoredUserRecord | None: ...
    def create_user(
        self,
        user_id: str,
        email: str,
        full_name: str,
        organization: str,
        role: UserRole,
        password_hash: str,
        username: str = "",
        is_verified: bool = True,
    ) -> StoredUserRecord: ...
    def store_verification_code(
        self, email: str, code: str, expires_at: str
    ) -> None: ...
    def get_verification_code(self, email: str) -> tuple[str, str] | None: ...
    def mark_email_verified(self, email: str) -> None: ...


class SqliteUserRepository:
    """Persists users in the `users` and `user_profiles` tables and seeds default accounts."""

    def __init__(self, db_manager: DatabaseManager, hasher: PasswordHasher) -> None:
        self._db = db_manager
        self._db.run_migrations()
        self._seed_defaults(hasher)

    def _seed_defaults(self, hasher: PasswordHasher) -> None:
        cursor = self._db.connection.cursor()
        cursor.execute("SELECT COUNT(*) AS cnt FROM users")
        row = cursor.fetchone()
        if row and int(row["cnt"]) > 0:
            return

        admin_hash = hasher.hash_password("scamguard2026")
        journalist_hash = hasher.hash_password("journalist2026")
        now_iso = "2026-09-18T10:00:00Z"

        cursor.execute(
            """
            INSERT OR IGNORE INTO users (
                id, email, full_name, organization, role, password_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "usr-elena-01",
                "elena.botnari@scamguard.md",
                "Elena Botnari",
                "Moldova Civic Media Lab",
                "admin",
                admin_hash,
                now_iso,
            ),
        )
        cursor.execute(
            """
            INSERT OR IGNORE INTO user_profiles (
                user_id, username, email, is_verified, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "usr-elena-01",
                "elena.botnari",
                "elena.botnari@scamguard.md",
                1,
                now_iso,
            ),
        )
        cursor.execute(
            """
            INSERT OR IGNORE INTO users (
                id, email, full_name, organization, role, password_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "usr-ion-02",
                "ion.rusu@scamguard.md",
                "Ion Rusu",
                "Chisinau Investigative Desk",
                "journalist",
                journalist_hash,
                now_iso,
            ),
        )
        cursor.execute(
            """
            INSERT OR IGNORE INTO user_profiles (
                user_id, username, email, is_verified, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "usr-ion-02",
                "ion.rusu",
                "ion.rusu@scamguard.md",
                1,
                now_iso,
            ),
        )
        self._db.connection.commit()

    @staticmethod
    def _row_to_record(row: Any) -> StoredUserRecord:
        keys = row.keys() if hasattr(row, "keys") else []
        username = str(row["username"]) if "username" in keys and row["username"] else ""
        has_verified_col = "is_verified" in keys and row["is_verified"] is not None
        is_verified_val = row["is_verified"] if has_verified_col else 1
        return StoredUserRecord(
            id=str(row["id"]),
            email=str(row["email"]),
            full_name=str(row["full_name"]),
            organization=str(row["organization"]),
            role=cast(UserRole, str(row["role"])),
            password_hash=str(row["password_hash"]),
            created_at=str(row["created_at"]),
            username=username or str(row["email"]).split("@")[0],
            is_verified=bool(is_verified_val),
        )

    def get_by_email(self, email: str) -> StoredUserRecord | None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT u.*, p.username, COALESCE(p.is_verified, 1) AS is_verified
            FROM users u
            LEFT JOIN user_profiles p ON u.id = p.user_id
            WHERE LOWER(u.email) = LOWER(?)
            LIMIT 1
            """,
            (email.strip(),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def get_by_username(self, username: str) -> StoredUserRecord | None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT u.*, p.username, COALESCE(p.is_verified, 1) AS is_verified
            FROM users u
            JOIN user_profiles p ON u.id = p.user_id
            WHERE LOWER(p.username) = LOWER(?)
            LIMIT 1
            """,
            (username.strip(),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def get_by_identifier(self, identifier: str) -> StoredUserRecord | None:
        clean = identifier.strip().lower()
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT u.*, p.username, COALESCE(p.is_verified, 1) AS is_verified
            FROM users u
            LEFT JOIN user_profiles p ON u.id = p.user_id
            WHERE LOWER(u.email) = ? OR LOWER(p.username) = ?
            LIMIT 1
            """,
            (clean, clean),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def get_by_id(self, user_id: str) -> StoredUserRecord | None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT u.*, p.username, COALESCE(p.is_verified, 1) AS is_verified
            FROM users u
            LEFT JOIN user_profiles p ON u.id = p.user_id
            WHERE u.id = ?
            LIMIT 1
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def create_user(
        self,
        user_id: str,
        email: str,
        full_name: str,
        organization: str,
        role: UserRole,
        password_hash: str,
        username: str = "",
        is_verified: bool = True,
    ) -> StoredUserRecord:
        now_iso = datetime.now(UTC).isoformat()
        resolved_username = username.strip().lower() or email.strip().lower().split("@")[0]
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO users (
                id, email, full_name, organization, role, password_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                email.strip().lower(),
                full_name.strip(),
                organization.strip() or "Independent Researcher",
                role,
                password_hash,
                now_iso,
            ),
        )
        cursor.execute(
            """
            INSERT OR REPLACE INTO user_profiles (
                user_id, username, email, is_verified, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                resolved_username,
                email.strip().lower(),
                1 if is_verified else 0,
                now_iso,
            ),
        )
        self._db.connection.commit()
        return StoredUserRecord(
            id=user_id,
            email=email.strip().lower(),
            full_name=full_name.strip(),
            organization=organization.strip() or "Independent Researcher",
            role=role,
            password_hash=password_hash,
            created_at=now_iso,
            username=resolved_username,
            is_verified=is_verified,
        )

    def store_verification_code(
        self, email: str, code: str, expires_at: str
    ) -> None:
        now_iso = datetime.now(UTC).isoformat()
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO email_verification_codes (
                email, code, created_at, expires_at
            ) VALUES (?, ?, ?, ?)
            """,
            (email.strip().lower(), code.strip(), now_iso, expires_at),
        )
        self._db.connection.commit()

    def get_verification_code(self, email: str) -> tuple[str, str] | None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT code, expires_at FROM email_verification_codes
            WHERE LOWER(email) = LOWER(?)
            LIMIT 1
            """,
            (email.strip(),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return str(row["code"]), str(row["expires_at"])

    def mark_email_verified(self, email: str) -> None:
        clean = email.strip().lower()
        cursor = self._db.connection.cursor()
        cursor.execute(
            "UPDATE user_profiles SET is_verified = 1 WHERE LOWER(email) = ?",
            (clean,),
        )
        cursor.execute(
            "DELETE FROM email_verification_codes WHERE LOWER(email) = ?",
            (clean,),
        )
        self._db.connection.commit()


class IParameterRepository(Protocol):
    def get_latest(self) -> SystemParametersDto: ...
    def create_version(
        self,
        version: str,
        similarity_threshold: float,
        time_window_minutes: int,
        collection_interval_minutes: int,
        min_cluster_channels: int,
        updated_by: str,
    ) -> SystemParametersDto: ...


class SqliteParameterRepository:
    """Persists immutable parameter versions in `parameter_sets`."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager
        self._db.run_migrations()

    def get_latest(self) -> SystemParametersDto:
        cursor = self._db.connection.cursor()
        cursor.execute("SELECT * FROM parameter_sets ORDER BY rowid DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return SystemParametersDto(
                parameterVersion="v1.4",
                similarityThreshold=0.82,
                timeWindowMinutes=30,
                collectionIntervalMinutes=5,
                minClusterChannels=3,
                updatedAt="2026-11-02T12:00:00Z",
                updatedBy="elena.botnari@scamguard.md",
            )
        return SystemParametersDto(
            parameterVersion=str(row["version"]),
            similarityThreshold=float(row["similarity_threshold"]),
            timeWindowMinutes=int(row["time_window_minutes"]),
            collectionIntervalMinutes=int(row["collection_interval_minutes"]),
            minClusterChannels=int(row["min_cluster_channels"]),
            updatedAt=str(row["created_at"]),
            updatedBy=str(row["created_by"]),
        )

    def create_version(
        self,
        version: str,
        similarity_threshold: float,
        time_window_minutes: int,
        collection_interval_minutes: int,
        min_cluster_channels: int,
        updated_by: str,
    ) -> SystemParametersDto:
        now_iso = datetime.now(UTC).isoformat()
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO parameter_sets (
                version,
                similarity_threshold,
                time_window_minutes,
                collection_interval_minutes,
                min_cluster_channels,
                created_at,
                created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version,
                similarity_threshold,
                time_window_minutes,
                collection_interval_minutes,
                min_cluster_channels,
                now_iso,
                updated_by,
            ),
        )
        self._db.connection.commit()
        return SystemParametersDto(
            parameterVersion=version,
            similarityThreshold=similarity_threshold,
            timeWindowMinutes=time_window_minutes,
            collectionIntervalMinutes=collection_interval_minutes,
            minClusterChannels=min_cluster_channels,
            updatedAt=now_iso,
            updatedBy=updated_by,
        )
