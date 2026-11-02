"""Repository layer for messages, raw texts, normalised hashes, checkpoints, and NFR-11 purging."""

from datetime import UTC, datetime
from typing import Protocol, cast

from app.db.database import DatabaseManager
from app.dtos.collector_dto import (
    CollectionRunDto,
    CollectionRunStatus,
    DetectedLanguage,
    NormalisedTextDto,
    PurgeDeletedPostReceiptDto,
    RawTelegramPostDto,
    StoredMessageDto,
)


class IMessageRepository(Protocol):
    def get_last_message_id(self, channel_id: str) -> int: ...
    def update_last_message_id(self, channel_id: str, last_id: int) -> None: ...
    def save_message(
        self, post: RawTelegramPostDto, norm: NormalisedTextDto
    ) -> tuple[StoredMessageDto, bool]: ...
    def get_message_by_id(self, message_id: str) -> StoredMessageDto | None: ...
    def list_messages(
        self, channel_id: str | None = None, limit: int = 100
    ) -> list[StoredMessageDto]: ...
    def purge_deleted_post_raw_text(
        self, message_id: str
    ) -> PurgeDeletedPostReceiptDto | None: ...
    def record_collection_run(self, run: CollectionRunDto) -> CollectionRunDto: ...
    def list_collection_runs(self, limit: int = 20) -> list[CollectionRunDto]: ...


class SqliteMessageRepository:
    """Stores Telegram messages with separated raw text and normalised text."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager
        self._db.run_migrations()

    def get_last_message_id(self, channel_id: str) -> int:
        cursor = self._db.connection.cursor()
        cursor.execute(
            "SELECT last_telegram_message_id FROM channel_checkpoints WHERE channel_id = ?",
            (channel_id,),
        )
        row = cursor.fetchone()
        return int(row["last_telegram_message_id"]) if row else 0

    def update_last_message_id(self, channel_id: str, last_id: int) -> None:
        now_iso = datetime.now(UTC).isoformat()
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO channel_checkpoints (channel_id, last_telegram_message_id, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
                last_telegram_message_id = MAX(
                    last_telegram_message_id, excluded.last_telegram_message_id
                ),
                updated_at = excluded.updated_at
            """,
            (channel_id, last_id, now_iso),
        )
        self._db.connection.commit()

    def save_message(
        self, post: RawTelegramPostDto, norm: NormalisedTextDto
    ) -> tuple[StoredMessageDto, bool]:
        message_id = f"msg-{post.channel_id}-{post.telegram_message_id}"
        existing = self.get_message_by_id(message_id)
        if existing is not None:
            return existing, False

        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO messages (
                id, channel_id, telegram_message_id, posted_at,
                forwarded_from, view_count, language, is_deleted_at_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                message_id,
                post.channel_id,
                post.telegram_message_id,
                post.posted_at,
                post.forwarded_from,
                post.view_count,
                norm.language,
            ),
        )
        cursor.execute(
            "INSERT INTO message_texts (message_id, raw_text) VALUES (?, ?)",
            (message_id, post.raw_text),
        )
        cursor.execute(
            """
            INSERT INTO message_norm (
                message_id, normalised_text, transliterated_text, text_hash
            ) VALUES (?, ?, ?, ?)
            """,
            (
                message_id,
                norm.normalised_text,
                norm.transliterated_text,
                norm.text_hash,
            ),
        )
        self._db.connection.commit()

        stored = StoredMessageDto(
            id=message_id,
            channelId=post.channel_id,
            telegramMessageId=post.telegram_message_id,
            postedAt=post.posted_at,
            forwardedFrom=post.forwarded_from,
            viewCount=post.view_count,
            language=norm.language,
            isDeletedAtSource=False,
            rawText=post.raw_text,
            normalisedText=norm.normalised_text,
            textHash=norm.text_hash,
        )
        return stored, True

    def get_message_by_id(self, message_id: str) -> StoredMessageDto | None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT
                m.id, m.channel_id, m.telegram_message_id, m.posted_at,
                m.forwarded_from, m.view_count, m.language, m.is_deleted_at_source,
                t.raw_text,
                n.normalised_text, n.text_hash
            FROM messages m
            INNER JOIN message_norm n ON n.message_id = m.id
            LEFT JOIN message_texts t ON t.message_id = m.id
            WHERE m.id = ?
            LIMIT 1
            """,
            (message_id,),
        )
        row = cursor.fetchone()
        return self._row_to_dto(row) if row else None

    def list_messages(
        self, channel_id: str | None = None, limit: int = 100
    ) -> list[StoredMessageDto]:
        cursor = self._db.connection.cursor()
        if channel_id:
            cursor.execute(
                """
                SELECT
                    m.id, m.channel_id, m.telegram_message_id, m.posted_at,
                    m.forwarded_from, m.view_count, m.language, m.is_deleted_at_source,
                    t.raw_text,
                    n.normalised_text, n.text_hash
                FROM messages m
                INNER JOIN message_norm n ON n.message_id = m.id
                LEFT JOIN message_texts t ON t.message_id = m.id
                WHERE m.channel_id = ?
                ORDER BY m.telegram_message_id ASC
                LIMIT ?
                """,
                (channel_id, limit),
            )
        else:
            cursor.execute(
                """
                SELECT
                    m.id, m.channel_id, m.telegram_message_id, m.posted_at,
                    m.forwarded_from, m.view_count, m.language, m.is_deleted_at_source,
                    t.raw_text,
                    n.normalised_text, n.text_hash
                FROM messages m
                INNER JOIN message_norm n ON n.message_id = m.id
                LEFT JOIN message_texts t ON t.message_id = m.id
                ORDER BY m.posted_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        return [self._row_to_dto(r) for r in cursor.fetchall()]

    def purge_deleted_post_raw_text(
        self, message_id: str
    ) -> PurgeDeletedPostReceiptDto | None:
        existing = self.get_message_by_id(message_id)
        if existing is None:
            return None

        cursor = self._db.connection.cursor()
        cursor.execute(
            "DELETE FROM message_texts WHERE message_id = ?",
            (message_id,),
        )
        cursor.execute(
            "UPDATE messages SET is_deleted_at_source = 1 WHERE id = ?",
            (message_id,),
        )
        self._db.connection.commit()
        return PurgeDeletedPostReceiptDto(
            messageId=message_id,
            rawTextPurged=True,
            retainedTextHash=existing.text_hash,
        )

    def record_collection_run(self, run: CollectionRunDto) -> CollectionRunDto:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO collection_runs (
                id, started_at, finished_at, status,
                channels_polled, messages_saved, flood_waits_count, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.id,
                run.started_at,
                run.finished_at,
                run.status,
                run.channels_polled,
                run.messages_saved,
                run.flood_waits_count,
                run.error_message,
            ),
        )
        self._db.connection.commit()
        return run

    def list_collection_runs(self, limit: int = 20) -> list[CollectionRunDto]:
        cursor = self._db.connection.cursor()
        cursor.execute(
            "SELECT * FROM collection_runs ORDER BY rowid DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        results: list[CollectionRunDto] = []
        for row in rows:
            mapping = cast(dict[str, object], row)
            results.append(
                CollectionRunDto(
                    id=str(mapping["id"]),
                    startedAt=str(mapping["started_at"]),
                    finishedAt=str(mapping["finished_at"]),
                    status=cast(
                        CollectionRunStatus,
                        str(mapping["status"]),
                    ),
                    channelsPolled=int(str(mapping["channels_polled"])),
                    messagesSaved=int(str(mapping["messages_saved"])),
                    floodWaitsCount=int(str(mapping["flood_waits_count"])),
                    errorMessage=(
                        str(mapping["error_message"])
                        if mapping["error_message"] is not None
                        else None
                    ),
                )
            )
        return results

    @staticmethod
    def _row_to_dto(row: object) -> StoredMessageDto:
        mapping = cast(dict[str, object], row)
        raw_val = mapping["raw_text"]
        fwd_val = mapping["forwarded_from"]
        return StoredMessageDto(
            id=str(mapping["id"]),
            channelId=str(mapping["channel_id"]),
            telegramMessageId=int(str(mapping["telegram_message_id"])),
            postedAt=str(mapping["posted_at"]),
            forwardedFrom=str(fwd_val) if fwd_val is not None else None,
            viewCount=int(str(mapping["view_count"])),
            language=cast(DetectedLanguage, str(mapping["language"])),
            isDeletedAtSource=bool(int(str(mapping["is_deleted_at_source"]))),
            rawText=str(raw_val) if raw_val is not None else None,
            normalisedText=str(mapping["normalised_text"]),
            textHash=str(mapping["text_hash"]),
        )
