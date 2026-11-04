"""Telegram public channel collector service with live MTProto support, FloodWait backoff, and data minimisation."""

import random
import re
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from app.core.errors import AppError
from app.core.logging import get_logger
from app.dtos.collector_dto import (
    CollectionRunDto,
    CollectionRunStatus,
    PurgeDeletedPostReceiptDto,
    RawTelegramPostDto,
    ResolvedChannelDto,
    StoredMessageDto,
)
from app.dtos.watchlist_dto import ChannelLanguage, WatchlistChannelDto
from app.repositories.message_repository import IMessageRepository
from app.repositories.watchlist_repository import IWatchlistRepository
from app.services.telegram_client import (
    FloodWaitError,
    ITelegramClientAdapter,
)
from app.services.text_normaliser import ITextNormaliser

logger = get_logger("collector")

_STANDARD_FOOTER_PATTERNS = [
    re.compile(
        r"^(?:.*?(?:Подписывайтесь|Следите|Abonați|Urmăriți|Canalul|Наш канал|Contact|Info|Sursa|Источник).*?)?(?:https?://)?(?:www\.)?t\.me/[a-zA-Z0-9_]+/?$",
        re.IGNORECASE,
    ),
    re.compile(r"^(?:Pentru detalii|Detalii|Подробнее|Читай дальше)[\s:]*(?:https?://\S+)?$", re.IGNORECASE),
]


def strip_channel_boilerplate(raw_text: str, known_patterns: list[str]) -> str:
    """Strips channel signatures, promo footers, and contact lines so they don't produce fake similarity."""
    cleaned = raw_text
    for pat in known_patterns:
        cleaned = cleaned.replace(pat, "")

    lines = cleaned.split("\n")
    kept_lines = []
    for line in lines:
        stripped = line.strip()
        if any(pat.match(stripped) for pat in _STANDARD_FOOTER_PATTERNS):
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines).strip()


class ICollectorService(Protocol):
    def resolve_and_add_channel(
        self, handle_or_url: str, added_by: str, backfill_days: int = 7
    ) -> WatchlistChannelDto: ...
    def poll_active_channels(self) -> CollectionRunDto: ...
    def backfill_channel(self, channel_id: str, days: int = 7) -> CollectionRunDto: ...
    def check_and_purge_deleted_posts(self, channel_id: str | None = None) -> int: ...
    def list_messages(
        self, channel_id: str | None = None, limit: int = 100
    ) -> list[StoredMessageDto]: ...
    def list_runs(self, channel_id: str | None = None, limit: int = 20) -> list[CollectionRunDto]: ...
    def purge_deleted_post(self, message_id: str) -> PurgeDeletedPostReceiptDto: ...


class TelegramCollectorService:
    """Polls active watchlist channels, cleans messy posts, and logs collection runs."""

    def __init__(
        self,
        watchlist_repo: IWatchlistRepository,
        message_repo: IMessageRepository,
        normaliser: ITextNormaliser,
        telegram_client: ITelegramClientAdapter,
        sleep_fn: Callable[[float], None] = time.sleep,
        max_retries: int = 3,
        add_jitter: bool = False,
        analysis_pipeline: object | None = None,
    ) -> None:
        self._watchlist_repo = watchlist_repo
        self._message_repo = message_repo
        self._normaliser = normaliser
        self._client = telegram_client
        self._sleep_fn = sleep_fn
        self._max_retries = max_retries
        self._add_jitter = add_jitter
        self._analysis_pipeline = analysis_pipeline

    def resolve_and_add_channel(
        self, handle_or_url: str, added_by: str, backfill_days: int = 7
    ) -> WatchlistChannelDto:
        """Resolves a public channel, adds it to watchlist, and initiates backfill."""
        resolved: ResolvedChannelDto = self._client.resolve_channel(handle_or_url)

        existing = self._watchlist_repo.get_by_handle(resolved.handle)
        if existing is not None:
            raise AppError(
                code="DUPLICATE_CHANNEL",
                message=f"Channel '{resolved.handle}' is already on the watch list.",
                status_code=409,
            )

        channel_id = f"ch-{resolved.handle.lstrip('@').lower().replace('_', '-')}"
        ch_lang: ChannelLanguage = "RO"
        if resolved.language_guess in ("RO", "RU", "MIXED"):
            ch_lang = resolved.language_guess  # type: ignore

        channel = self._watchlist_repo.create_channel(
            channel_id=channel_id,
            handle=resolved.handle,
            title=resolved.title,
            language=ch_lang,
            added_by=added_by,
            subscribers_count=resolved.subscribers_count,
            telegram_channel_id=resolved.telegram_channel_id,
        )

        # Backfill initial messages
        try:
            self.backfill_channel(channel_id=channel.id, days=backfill_days)
        except Exception as exc:
            logger.warning(f"Initial backfill failed for {channel.handle}: {exc}")

        return channel

    def backfill_channel(self, channel_id: str, days: int = 7) -> CollectionRunDto:
        """Loads the last N days of messages in batches, oldest first."""
        channel = self._watchlist_repo.get_by_id(channel_id)
        if channel is None:
            raise AppError(
                code="CHANNEL_NOT_FOUND",
                message=f"Channel '{channel_id}' not found.",
                status_code=404,
            )

        started_at = datetime.now(UTC).isoformat()
        messages_saved = 0
        flood_waits_count = 0
        errors: list[str] = []

        try:
            posts = self._client.fetch_messages_backfill(
                channel_id=channel.id, handle=channel.handle, days=days
            )
            messages_saved = self._store_fetched_posts(channel.id, posts)
            now_iso = datetime.now(UTC).isoformat()
            self._watchlist_repo.update_last_collection(channel.id, now_iso, last_error=None)
            if messages_saved > 0 and self._analysis_pipeline is not None:
                try:
                    self._analysis_pipeline.run_analysis_pipeline()  # type: ignore[attr-defined]
                except Exception as exc:
                    logger.warning(f"Post-backfill analysis pipeline run failed: {exc}")
        except FloodWaitError as flood_err:
            flood_waits_count += 1
            errors.append(f"FloodWait: wait {flood_err.seconds}s")
        except Exception as exc:
            errors.append(str(exc))
            self._watchlist_repo.update_last_collection(
                channel.id, datetime.now(UTC).isoformat(), last_error=str(exc)
            )

        finished_at = datetime.now(UTC).isoformat()
        status: CollectionRunStatus = "completed" if not errors else "failed"
        run = CollectionRunDto(
            id=f"run-{secrets.token_hex(4)}",
            channelId=channel.id,
            startedAt=started_at,
            finishedAt=finished_at,
            status=status,
            channelsPolled=1,
            messagesSaved=messages_saved,
            floodWaitsCount=flood_waits_count,
            errorMessage="; ".join(errors) if errors else None,
        )
        return self._message_repo.record_collection_run(run)

    def poll_active_channels(self) -> CollectionRunDto:
        """Incremental polling of active channels with retry, exponential backoff, and run logging."""
        started_at = datetime.now(UTC).isoformat()
        channels, _ = self._watchlist_repo.list_paginated(page=1, page_size=500)
        active_channels = [ch for ch in channels if ch.status == "active"]

        channels_polled = 0
        messages_saved = 0
        flood_waits_count = 0
        errors: list[str] = []

        for channel in active_channels:
            last_id = self._message_repo.get_last_message_id(channel.id)
            attempt = 0
            fetched_posts: list[RawTelegramPostDto] | None = None

            while attempt < self._max_retries:
                attempt += 1
                try:
                    fetched_posts = self._client.fetch_messages_since(
                        channel_id=channel.id,
                        handle=channel.handle,
                        min_message_id=last_id,
                    )
                    break
                except FloodWaitError as flood_err:
                    flood_waits_count += 1
                    wait_time = float(flood_err.seconds)
                    if self._add_jitter:
                        wait_time += random.uniform(1.0, 3.0)
                    logger.warning(
                        f"FloodWaitError on {channel.handle}: sleeping {wait_time:.1f}s"
                    )
                    self._sleep_fn(wait_time)
                except Exception as exc:
                    backoff = float(2 ** (attempt - 1))
                    if self._add_jitter:
                        backoff += random.uniform(0.5, 1.5)
                    logger.error(f"Error polling {channel.handle} (attempt {attempt}): {exc}")
                    if attempt >= self._max_retries:
                        errors.append(f"{channel.handle}: {exc}")
                        # Pause channel collection if persistent failure, without stopping others
                        self._watchlist_repo.update_status(channel.id, "paused")
                        self._watchlist_repo.update_last_collection(
                            channel.id, datetime.now(UTC).isoformat(), last_error=str(exc)
                        )
                    else:
                        self._sleep_fn(backoff)

            if fetched_posts is None:
                continue

            channels_polled += 1
            saved = self._store_fetched_posts(channel.id, fetched_posts)
            messages_saved += saved
            self._watchlist_repo.update_last_collection(
                channel.id, datetime.now(UTC).isoformat(), last_error=None
            )

        if messages_saved > 0 and self._analysis_pipeline is not None:
            try:
                self._analysis_pipeline.run_analysis_pipeline()  # type: ignore[attr-defined]
            except Exception as exc:
                logger.warning(f"Post-collection analysis pipeline run failed: {exc}")

        finished_at = datetime.now(UTC).isoformat()
        status: CollectionRunStatus = (
            "completed" if not errors else ("partial" if channels_polled > 0 else "failed")
        )
        run = CollectionRunDto(
            id=f"run-{secrets.token_hex(4)}",
            channelId=None,
            startedAt=started_at,
            finishedAt=finished_at,
            status=status,
            channelsPolled=channels_polled,
            messagesSaved=messages_saved,
            floodWaitsCount=flood_waits_count,
            errorMessage="; ".join(errors) if errors else None,
        )
        return self._message_repo.record_collection_run(run)

    def _store_fetched_posts(self, channel_id: str, posts: list[RawTelegramPostDto]) -> int:
        """Stores posts, strips boilerplate, handles edits, and advances channel checkpoint."""
        last_id = self._message_repo.get_last_message_id(channel_id)
        highest_id = last_id
        messages_saved = 0

        known_boilerplates = self._message_repo.get_channel_boilerplates(channel_id)
        self._detect_and_register_boilerplates(channel_id, posts)

        for post in sorted(posts, key=lambda p: p.telegram_message_id):
            cleaned_text = strip_channel_boilerplate(post.raw_text, known_boilerplates)
            norm = self._normaliser.normalise(cleaned_text)

            _, created = self._message_repo.save_message(post=post, norm=norm)
            if created:
                messages_saved += 1
            if post.telegram_message_id > highest_id:
                highest_id = post.telegram_message_id

        if highest_id > last_id:
            self._message_repo.update_last_message_id(channel_id, highest_id)

        return messages_saved

    def _detect_and_register_boilerplates(
        self, channel_id: str, posts: list[RawTelegramPostDto]
    ) -> None:
        """Detects recurring lines across posts (>50% frequency) and registers as boilerplate."""
        if len(posts) < 4:
            return

        line_counts: dict[str, int] = {}
        for post in posts:
            for line in post.raw_text.split("\n"):
                stripped = line.strip()
                if len(stripped) > 15:
                    line_counts[stripped] = line_counts.get(stripped, 0) + 1

        threshold = max(3, int(len(posts) * 0.5))
        for line, count in line_counts.items():
            if count >= threshold:
                self._message_repo.add_channel_boilerplate(channel_id, line)

    def check_and_purge_deleted_posts(self, channel_id: str | None = None) -> int:
        """Checks if recent messages exist at source. If deleted, purges raw text and sets deleted_at."""
        channels: list[WatchlistChannelDto] = []
        if channel_id:
            ch = self._watchlist_repo.get_by_id(channel_id)
            if ch:
                channels = [ch]
        else:
            paged, _ = self._watchlist_repo.list_paginated(page=1, page_size=500)
            channels = [c for c in paged if c.status == "active"]

        total_purged = 0
        for channel in channels:
            recent_msgs = self._message_repo.get_messages_for_deletion_check(channel.id, limit=50)
            if not recent_msgs:
                continue

            ids = [m.telegram_message_id for m in recent_msgs]
            try:
                existing_ids = self._client.check_messages_exist(channel.id, channel.handle, ids)
            except Exception as exc:
                logger.error(f"Failed to check message existence for {channel.handle}: {exc}")
                continue

            for msg in recent_msgs:
                if msg.telegram_message_id not in existing_ids:
                    logger.info(
                        f"Post {msg.id} ({channel.handle}/{msg.telegram_message_id}) was deleted at source. Purging raw text."
                    )
                    self._message_repo.mark_message_deleted(msg.id)
                    total_purged += 1

        return total_purged

    def list_messages(
        self, channel_id: str | None = None, limit: int = 100
    ) -> list[StoredMessageDto]:
        return self._message_repo.list_messages(channel_id=channel_id, limit=limit)

    def list_runs(self, channel_id: str | None = None, limit: int = 20) -> list[CollectionRunDto]:
        return self._message_repo.list_collection_runs(channel_id=channel_id, limit=limit)

    def purge_deleted_post(self, message_id: str) -> PurgeDeletedPostReceiptDto:
        receipt = self._message_repo.purge_deleted_post_raw_text(message_id)
        if receipt is None:
            raise AppError(
                code="MESSAGE_NOT_FOUND",
                message=f"Message '{message_id}' was not found.",
                status_code=404,
            )
        return receipt
