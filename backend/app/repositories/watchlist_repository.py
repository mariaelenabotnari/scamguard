"""Repository layer for monitored Telegram channels on the watch list."""

from datetime import UTC, datetime
import sqlite3
from typing import Protocol, cast

from app.db.database import DatabaseManager
from app.dtos.watchlist_dto import ChannelLanguage, WatchlistChannelDto, WatchlistStatus


class IWatchlistRepository(Protocol):
    def list_paginated(
        self, page: int, page_size: int
    ) -> tuple[list[WatchlistChannelDto], int]: ...
    def get_by_handle(self, handle: str) -> WatchlistChannelDto | None: ...
    def get_by_id(self, channel_id: str) -> WatchlistChannelDto | None: ...
    def create_channel(
        self,
        channel_id: str,
        handle: str,
        title: str,
        language: ChannelLanguage,
        added_by: str,
        subscribers_count: int = 1200,
        telegram_channel_id: int | None = None,
    ) -> WatchlistChannelDto: ...
    def update_last_collection(
        self, channel_id: str, last_collected_at: str, last_error: str | None = None
    ) -> None: ...
    def update_metadata(
        self,
        channel_id: str,
        telegram_channel_id: int | None = None,
        title: str | None = None,
        subscribers_count: int | None = None,
    ) -> None: ...
    def update_status(
        self, channel_id: str, status: WatchlistStatus
    ) -> WatchlistChannelDto | None: ...
    def delete_channel(self, channel_id: str) -> bool: ...


class SqliteWatchlistRepository:
    """Persists watchlist channels in `watchlist_channels` with pagination and seeding."""

    def __init__(self, db_manager: DatabaseManager, seed_defaults: bool = True) -> None:
        self._db = db_manager
        self._db.run_migrations()
        if seed_defaults:
            self._seed_defaults()

    def _seed_defaults(self) -> None:
        cursor = self._db.connection.cursor()
        cursor.execute("SELECT COUNT(*) AS cnt FROM watchlist_channels")
        row = cursor.fetchone()
        if row and int(row["cnt"]) > 0:
            return

        defaults: list[tuple[str, str, str, str, str, str, str, int]] = [
            (
                "ch-01",
                "@moldova_azi_info",
                "Moldova Azi Info",
                "RO",
                "active",
                "elena.botnari",
                "2026-10-14",
                48200,
            ),
            (
                "ch-02",
                "@chisinau_express",
                "Chișinău Express 24",
                "RO",
                "active",
                "elena.botnari",
                "2026-10-14",
                31900,
            ),
            (
                "ch-03",
                "@pridnestrovie_pulse",
                "Приднестровье Пульс",
                "RU",
                "active",
                "ion.rusu",
                "2026-10-16",
                64500,
            ),
            (
                "ch-04",
                "@gagauzia_voice",
                "Gagauzia Voice",
                "MIXED",
                "paused",
                "ion.rusu",
                "2026-10-18",
                19400,
            ),
        ]
        cursor.executemany(
            """
            INSERT OR IGNORE INTO watchlist_channels (
                id, handle, title, language, status, added_by, added_at, subscribers_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            defaults,
        )
        self._db.connection.commit()

    def list_paginated(self, page: int, page_size: int) -> tuple[list[WatchlistChannelDto], int]:
        cursor = self._db.connection.cursor()
        cursor.execute("SELECT COUNT(*) AS cnt FROM watchlist_channels")
        count_row = cursor.fetchone()
        total = int(count_row["cnt"]) if count_row else 0

        offset = max(0, (page - 1) * page_size)
        cursor.execute(
            """
            SELECT * FROM watchlist_channels
            ORDER BY rowid DESC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        )
        rows = cursor.fetchall()
        return [self._row_to_dto(row) for row in rows], total

    def get_by_handle(self, handle: str) -> WatchlistChannelDto | None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            "SELECT * FROM watchlist_channels WHERE LOWER(handle) = LOWER(?) LIMIT 1",
            (handle.strip(),),
        )
        row = cursor.fetchone()
        return self._row_to_dto(row) if row else None

    def get_by_id(self, channel_id: str) -> WatchlistChannelDto | None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            "SELECT * FROM watchlist_channels WHERE id = ? LIMIT 1",
            (channel_id,),
        )
        row = cursor.fetchone()
        return self._row_to_dto(row) if row else None

    def create_channel(
        self,
        channel_id: str,
        handle: str,
        title: str,
        language: ChannelLanguage,
        added_by: str,
        subscribers_count: int = 1200,
        telegram_channel_id: int | None = None,
    ) -> WatchlistChannelDto:
        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO watchlist_channels (
                id, handle, title, language, status, added_by, added_at, subscribers_count, telegram_channel_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                channel_id,
                handle,
                title,
                language,
                "active",
                added_by,
                today_str,
                subscribers_count,
                telegram_channel_id,
            ),
        )
        self._db.connection.commit()
        return WatchlistChannelDto(
            id=channel_id,
            handle=handle,
            title=title,
            language=language,
            status="active",
            addedBy=added_by,
            addedAt=today_str,
            subscribersCount=subscribers_count,
            telegramChannelId=telegram_channel_id,
        )

    def update_last_collection(
        self, channel_id: str, last_collected_at: str, last_error: str | None = None
    ) -> None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            UPDATE watchlist_channels
            SET last_collected_at = ?, last_error = ?
            WHERE id = ?
            """,
            (last_collected_at, last_error, channel_id),
        )
        self._db.connection.commit()

    def update_metadata(
        self,
        channel_id: str,
        telegram_channel_id: int | None = None,
        title: str | None = None,
        subscribers_count: int | None = None,
    ) -> None:
        cursor = self._db.connection.cursor()
        updates: list[str] = []
        params: list[object] = []
        if telegram_channel_id is not None:
            updates.append("telegram_channel_id = ?")
            params.append(telegram_channel_id)
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if subscribers_count is not None:
            updates.append("subscribers_count = ?")
            params.append(subscribers_count)
        if updates:
            params.append(channel_id)
            cursor.execute(
                f"UPDATE watchlist_channels SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            self._db.connection.commit()

    def update_status(self, channel_id: str, status: WatchlistStatus) -> WatchlistChannelDto | None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            "UPDATE watchlist_channels SET status = ? WHERE id = ?",
            (status, channel_id),
        )
        self._db.connection.commit()
        return self.get_by_id(channel_id)

    def delete_channel(self, channel_id: str) -> bool:
        cursor = self._db.connection.cursor()
        cursor.execute("DELETE FROM watchlist_channels WHERE id = ?", (channel_id,))
        deleted = cursor.rowcount > 0
        self._db.connection.commit()
        return deleted

    @staticmethod
    def _row_to_dto(row: object) -> WatchlistChannelDto:
        mapping = dict(cast(sqlite3.Row, row))
        tg_id = mapping.get("telegram_channel_id")
        last_coll = mapping.get("last_collected_at")
        last_err = mapping.get("last_error")
        return WatchlistChannelDto(
            id=str(mapping["id"]),
            handle=str(mapping["handle"]),
            title=str(mapping["title"]),
            language=cast(ChannelLanguage, str(mapping["language"])),
            status=cast(WatchlistStatus, str(mapping["status"])),
            addedBy=str(mapping["added_by"]),
            addedAt=str(mapping["added_at"]),
            subscribersCount=int(str(mapping["subscribers_count"])),
            telegramChannelId=int(tg_id) if tg_id is not None else None,
            lastCollectedAt=str(last_coll) if last_coll is not None else None,
            lastError=str(last_err) if last_err is not None else None,
        )
