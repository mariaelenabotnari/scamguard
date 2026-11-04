"""Repository layer for messages, raw texts, normalised hashes, checkpoints, and post purging."""

import sqlite3
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
    def purge_deleted_post_raw_text(self, message_id: str) -> PurgeDeletedPostReceiptDto | None: ...
    def mark_message_deleted(self, message_id: str) -> None: ...
    def record_collection_run(self, run: CollectionRunDto) -> CollectionRunDto: ...
    def list_collection_runs(
        self, channel_id: str | None = None, limit: int = 20
    ) -> list[CollectionRunDto]: ...
    def record_message_edit(
        self, message_id: str, old_raw_text: str, new_raw_text: str, edited_at: str
    ) -> None: ...
    def get_channel_boilerplates(self, channel_id: str) -> list[str]: ...
    def add_channel_boilerplate(self, channel_id: str, pattern: str) -> None: ...
    def get_messages_for_deletion_check(
        self, channel_id: str, limit: int = 50
    ) -> list[StoredMessageDto]: ...


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
        now_iso = datetime.now(UTC).isoformat()

        # Handle edit detection
        if existing is not None:
            # Check if post was edited
            is_edited = (
                post.edit_date is not None
                and (existing.edit_date != post.edit_date or (existing.raw_text and existing.raw_text != post.raw_text))
            )
            if is_edited and existing.raw_text:
                self.record_message_edit(
                    message_id=message_id,
                    old_raw_text=existing.raw_text,
                    new_raw_text=post.raw_text,
                    edited_at=post.edit_date or now_iso,
                )
                cursor = self._db.connection.cursor()
                cursor.execute(
                    "UPDATE message_texts SET raw_text = ? WHERE message_id = ?",
                    (post.raw_text, message_id),
                )
                cursor.execute(
                    """
                    UPDATE message_norm
                    SET normalised_text = ?, transliterated_text = ?, text_hash = ?
                    WHERE message_id = ?
                    """,
                    (norm.normalised_text, norm.transliterated_text, norm.text_hash, message_id),
                )
                cursor.execute(
                    """
                    UPDATE messages
                    SET edit_date = ?, last_seen_at = ?, view_count = ?, forwards = ?
                    WHERE id = ?
                    """,
                    (post.edit_date, now_iso, post.view_count, post.forwards, message_id),
                )
                self._db.connection.commit()
                updated = self.get_message_by_id(message_id)
                return (updated if updated is not None else existing), False

            # Not edited: update last seen & counters
            cursor = self._db.connection.cursor()
            cursor.execute(
                "UPDATE messages SET last_seen_at = ?, view_count = ?, forwards = ? WHERE id = ?",
                (now_iso, post.view_count, post.forwards, message_id),
            )
            self._db.connection.commit()
            return existing, False

        # New message
        first_seen = post.first_seen_at or now_iso
        last_seen = post.last_seen_at or now_iso
        skip_sim = 1 if (
            post.has_media and not post.raw_text.strip()
            or len(norm.normalised_text.strip()) < 25
        ) else 0

        post_link = post.post_link or f"https://t.me/{post.channel_id.replace('ch-', '')}/{post.telegram_message_id}"

        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO messages (
                id, channel_id, telegram_message_id, posted_at,
                forwarded_from, view_count, language, is_deleted_at_source,
                has_media, media_type, forwards, edit_date, grouped_id,
                is_forward, forward_source_channel_id, forward_source_name,
                forward_source_date, reply_to_id, post_link, first_seen_at,
                last_seen_at, deleted_at, skip_similarity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
            """,
            (
                message_id,
                post.channel_id,
                post.telegram_message_id,
                post.posted_at,
                post.forwarded_from,
                post.view_count,
                norm.language,
                1 if post.has_media else 0,
                post.media_type,
                post.forwards,
                post.edit_date,
                str(post.grouped_id) if post.grouped_id is not None else None,
                1 if post.is_forward else 0,
                post.forward_source_channel_id,
                post.forward_source_name,
                post.forward_source_date,
                post.reply_to_id,
                post_link,
                first_seen,
                last_seen,
                skip_sim,
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

        stored = self.get_message_by_id(message_id)
        if stored is None:
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
                hasMedia=post.has_media,
                mediaType=post.media_type,
                forwards=post.forwards,
                editDate=post.edit_date,
                groupedId=str(post.grouped_id) if post.grouped_id is not None else None,
                isForward=post.is_forward,
                forwardSourceChannelId=post.forward_source_channel_id,
                forwardSourceName=post.forward_source_name,
                forwardSourceDate=post.forward_source_date,
                replyToId=post.reply_to_id,
                postLink=post_link,
                firstSeenAt=first_seen,
                lastSeenAt=last_seen,
                deletedAt=None,
                skipSimilarity=bool(skip_sim),
            )
        return stored, True

    def record_message_edit(
        self, message_id: str, old_raw_text: str, new_raw_text: str, edited_at: str
    ) -> None:
        import secrets
        edit_id = f"edit-{secrets.token_hex(6)}"
        now_iso = datetime.now(UTC).isoformat()
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO message_edits (
                id, message_id, old_raw_text, new_raw_text, edited_at, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (edit_id, message_id, old_raw_text, new_raw_text, edited_at, now_iso),
        )
        self._db.connection.commit()

    def get_channel_boilerplates(self, channel_id: str) -> list[str]:
        cursor = self._db.connection.cursor()
        cursor.execute(
            "SELECT boilerplate_text FROM channel_boilerplates WHERE channel_id = ?",
            (channel_id,),
        )
        return [str(row["boilerplate_text"]) for row in cursor.fetchall()]

    def add_channel_boilerplate(self, channel_id: str, pattern: str) -> None:
        now_iso = datetime.now(UTC).isoformat()
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO channel_boilerplates (channel_id, boilerplate_text, created_at)
            VALUES (?, ?, ?)
            """,
            (channel_id, pattern.strip(), now_iso),
        )
        self._db.connection.commit()

    def get_messages_for_deletion_check(
        self, channel_id: str, limit: int = 50
    ) -> list[StoredMessageDto]:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT
                m.*,
                t.raw_text,
                n.normalised_text, n.text_hash
            FROM messages m
            INNER JOIN message_norm n ON n.message_id = m.id
            LEFT JOIN message_texts t ON t.message_id = m.id
            WHERE m.channel_id = ? AND m.is_deleted_at_source = 0
            ORDER BY m.posted_at DESC
            LIMIT ?
            """,
            (channel_id, limit),
        )
        return [self._row_to_dto(r) for r in cursor.fetchall()]

    def mark_message_deleted(self, message_id: str) -> None:
        now_iso = datetime.now(UTC).isoformat()
        cursor = self._db.connection.cursor()
        cursor.execute(
            "DELETE FROM message_texts WHERE message_id = ?",
            (message_id,),
        )
        cursor.execute(
            """
            UPDATE messages
            SET is_deleted_at_source = 1, deleted_at = ?
            WHERE id = ?
            """,
            (now_iso, message_id),
        )
        self._db.connection.commit()

    def get_message_by_id(self, message_id: str) -> StoredMessageDto | None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT
                m.*,
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
                    m.*,
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
                    m.*,
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

    def purge_deleted_post_raw_text(self, message_id: str) -> PurgeDeletedPostReceiptDto | None:
        existing = self.get_message_by_id(message_id)
        if existing is None:
            return None

        now_iso = datetime.now(UTC).isoformat()
        cursor = self._db.connection.cursor()
        cursor.execute(
            "DELETE FROM message_texts WHERE message_id = ?",
            (message_id,),
        )
        cursor.execute(
            """
            UPDATE messages
            SET is_deleted_at_source = 1, deleted_at = COALESCE(deleted_at, ?)
            WHERE id = ?
            """,
            (now_iso, message_id),
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
                id, channel_id, started_at, finished_at, status,
                channels_polled, messages_saved, flood_waits_count, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.id,
                run.channel_id,
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

    def list_collection_runs(
        self, channel_id: str | None = None, limit: int = 20
    ) -> list[CollectionRunDto]:
        cursor = self._db.connection.cursor()
        if channel_id:
            cursor.execute(
                "SELECT * FROM collection_runs WHERE channel_id = ? ORDER BY rowid DESC LIMIT ?",
                (channel_id, limit),
            )
        else:
            cursor.execute(
                "SELECT * FROM collection_runs ORDER BY rowid DESC LIMIT ?",
                (limit,),
            )
        rows = cursor.fetchall()
        results: list[CollectionRunDto] = []
        for row in rows:
            mapping = dict(cast(sqlite3.Row, row))
            results.append(
                CollectionRunDto(
                    id=str(mapping["id"]),
                    channelId=str(mapping["channel_id"]) if mapping.get("channel_id") else None,
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
        mapping = dict(cast(sqlite3.Row, row))
        raw_val = mapping.get("raw_text")
        fwd_val = mapping.get("forwarded_from")
        fwd_src_id = mapping.get("forward_source_channel_id")
        fwd_src_name = mapping.get("forward_source_name")
        fwd_src_date = mapping.get("forward_source_date")
        media_type = mapping.get("media_type")
        edit_date = mapping.get("edit_date")
        grouped_id = mapping.get("grouped_id")
        reply_to_id = mapping.get("reply_to_id")
        post_link = mapping.get("post_link")
        first_seen = mapping.get("first_seen_at")
        last_seen = mapping.get("last_seen_at")
        deleted_at = mapping.get("deleted_at")

        return StoredMessageDto(
            id=str(mapping["id"]),
            channelId=str(mapping["channel_id"]),
            telegramMessageId=int(str(mapping["telegram_message_id"])),
            postedAt=str(mapping["posted_at"]),
            forwardedFrom=str(fwd_val) if fwd_val is not None else None,
            viewCount=int(str(mapping.get("view_count", 0))),
            language=cast(DetectedLanguage, str(mapping.get("language", "RO"))),
            isDeletedAtSource=bool(int(str(mapping.get("is_deleted_at_source", 0)))),
            rawText=str(raw_val) if raw_val is not None else None,
            normalisedText=str(mapping["normalised_text"]),
            textHash=str(mapping["text_hash"]),
            hasMedia=bool(int(str(mapping.get("has_media", 0)))),
            mediaType=str(media_type) if media_type is not None else None,
            forwards=int(str(mapping.get("forwards", 0))),
            editDate=str(edit_date) if edit_date is not None else None,
            groupedId=str(grouped_id) if grouped_id is not None else None,
            isForward=bool(int(str(mapping.get("is_forward", 0)))),
            forwardSourceChannelId=str(fwd_src_id) if fwd_src_id is not None else None,
            forwardSourceName=str(fwd_src_name) if fwd_src_name is not None else None,
            forwardSourceDate=str(fwd_src_date) if fwd_src_date is not None else None,
            replyToId=int(str(reply_to_id)) if reply_to_id is not None else None,
            postLink=str(post_link) if post_link is not None else None,
            firstSeenAt=str(first_seen) if first_seen is not None else None,
            lastSeenAt=str(last_seen) if last_seen is not None else None,
            deletedAt=str(deleted_at) if deleted_at is not None else None,
            skipSimilarity=bool(int(str(mapping.get("skip_similarity", 0)))),
        )
