"""Telegram public channel collector service with FloodWait backoff and NFR-11 purge."""

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
    StoredMessageDto,
)
from app.repositories.message_repository import IMessageRepository
from app.repositories.watchlist_repository import IWatchlistRepository
from app.services.text_normaliser import ITextNormaliser

logger = get_logger("collector")


class FloodWaitError(Exception):
    """Represents Telegram MTProto FloodWaitError with required wait seconds."""

    def __init__(self, seconds: int) -> None:
        super().__init__(f"Telegram FloodWaitError: wait {seconds} seconds")
        self.seconds = seconds


class ITelegramClientAdapter(Protocol):
    def fetch_messages_since(
        self, channel_id: str, handle: str, min_message_id: int
    ) -> list[RawTelegramPostDto]: ...


class FakeTelegramClientAdapter:
    """Deterministic Telegram client adapter for testing 5+ channels and FloodWait recovery."""

    def __init__(
        self,
        channel_posts: dict[str, list[RawTelegramPostDto]] | None = None,
        flood_wait_once_channels: dict[str, int] | None = None,
    ) -> None:
        self._posts = channel_posts if channel_posts is not None else self._default_posts()
        self._flood_wait_once = dict(flood_wait_once_channels or {})

    def fetch_messages_since(
        self, channel_id: str, handle: str, min_message_id: int
    ) -> list[RawTelegramPostDto]:
        if channel_id in self._flood_wait_once:
            wait_sec = self._flood_wait_once.pop(channel_id)
            raise FloodWaitError(seconds=wait_sec)

        posts = self._posts.get(channel_id, [])
        return [
            p
            for p in posts
            if p.telegram_message_id > min_message_id
        ]

    @staticmethod
    def _default_posts() -> dict[str, list[RawTelegramPostDto]]:
        return {
            "ch-01": [
                RawTelegramPostDto(
                    channelId="ch-01",
                    telegramMessageId=101,
                    rawText=(
                        "URGENT! Tarifele la energie în Chișinău vor exploda cu 300% "
                        "după directiva de la Bruxelles! https://t.me/moldova_azi_info/101"
                    ),
                    postedAt="2026-11-02T10:01:00Z",
                    forwardedFrom=None,
                    viewCount=4120,
                ),
            ],
            "ch-02": [
                RawTelegramPostDto(
                    channelId="ch-02",
                    telegramMessageId=201,
                    rawText=(
                        "URGENT: Tarifele la energie în Chişinău vor exploda cu 300% "
                        "după directiva de la Bruxelles!"
                    ),
                    postedAt="2026-11-02T10:03:00Z",
                    forwardedFrom="@moldova_azi_info",
                    viewCount=3890,
                ),
            ],
            "ch-03": [
                RawTelegramPostDto(
                    channelId="ch-03",
                    telegramMessageId=301,
                    rawText=(
                        "СРОЧНО! Тарифы на газ и свет в Молдове вырастут на 300% "
                        "по требованию ЕС! https://t.me/pridnestrovie_pulse/301"
                    ),
                    postedAt="2026-11-02T10:04:00Z",
                    forwardedFrom=None,
                    viewCount=6100,
                ),
            ],
        }


class ICollectorService(Protocol):
    def poll_active_channels(self) -> CollectionRunDto: ...
    def list_messages(
        self, channel_id: str | None = None, limit: int = 100
    ) -> list[StoredMessageDto]: ...
    def list_runs(self, limit: int = 20) -> list[CollectionRunDto]: ...
    def purge_deleted_post(self, message_id: str) -> PurgeDeletedPostReceiptDto: ...


class TelegramCollectorService:
    """Polls active watchlist channels, normalises messages, and purges deleted posts."""

    def __init__(
        self,
        watchlist_repo: IWatchlistRepository,
        message_repo: IMessageRepository,
        normaliser: ITextNormaliser,
        telegram_client: ITelegramClientAdapter,
        sleep_fn: Callable[[float], None] = time.sleep,
        max_retries: int = 3,
    ) -> None:
        self._watchlist_repo = watchlist_repo
        self._message_repo = message_repo
        self._normaliser = normaliser
        self._client = telegram_client
        self._sleep_fn = sleep_fn
        self._max_retries = max_retries

    def poll_active_channels(self) -> CollectionRunDto:
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
                    logger.warning(
                        f"FloodWaitError on {channel.handle}: sleeping {flood_err.seconds}s"
                    )
                    self._sleep_fn(float(flood_err.seconds))
                except Exception as exc:
                    backoff = float(2 ** (attempt - 1))
                    logger.error(
                        f"Error polling {channel.handle} (attempt {attempt}): {exc}"
                    )
                    if attempt >= self._max_retries:
                        errors.append(f"{channel.handle}: {exc}")
                    else:
                        self._sleep_fn(backoff)

            if fetched_posts is None:
                continue

            channels_polled += 1
            highest_id = last_id
            for post in sorted(fetched_posts, key=lambda p: p.telegram_message_id):
                norm = self._normaliser.normalise(post.raw_text)
                _, created = self._message_repo.save_message(post=post, norm=norm)
                if created:
                    messages_saved += 1
                if post.telegram_message_id > highest_id:
                    highest_id = post.telegram_message_id

            if highest_id > last_id:
                self._message_repo.update_last_message_id(channel.id, highest_id)

        finished_at = datetime.now(UTC).isoformat()
        status: CollectionRunStatus = (
            "completed" if not errors else ("partial" if channels_polled > 0 else "failed")
        )
        run = CollectionRunDto(
            id=f"run-{secrets.token_hex(4)}",
            startedAt=started_at,
            finishedAt=finished_at,
            status=status,
            channelsPolled=channels_polled,
            messagesSaved=messages_saved,
            floodWaitsCount=flood_waits_count,
            errorMessage="; ".join(errors) if errors else None,
        )
        return self._message_repo.record_collection_run(run)

    def list_messages(
        self, channel_id: str | None = None, limit: int = 100
    ) -> list[StoredMessageDto]:
        return self._message_repo.list_messages(channel_id=channel_id, limit=limit)

    def list_runs(self, limit: int = 20) -> list[CollectionRunDto]:
        return self._message_repo.list_collection_runs(limit=limit)

    def purge_deleted_post(self, message_id: str) -> PurgeDeletedPostReceiptDto:
        receipt = self._message_repo.purge_deleted_post_raw_text(message_id)
        if receipt is None:
            raise AppError(
                code="MESSAGE_NOT_FOUND",
                message=f"Message '{message_id}' was not found.",
                status_code=404,
            )
        return receipt
