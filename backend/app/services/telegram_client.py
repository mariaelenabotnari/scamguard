"""Telegram client adapters for ScamGuard: Telethon MTProto adapter and deterministic Fake adapter."""

import asyncio
import concurrent.futures
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, cast

from app.core.errors import AppError
from app.core.logging import get_logger
from app.dtos.collector_dto import RawTelegramPostDto, ResolvedChannelDto

logger = get_logger("telegram_client")


def _run_async(coro: Any) -> Any:
    """Executes an async coroutine synchronously, safely handling running event loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


class FloodWaitError(Exception):
    """Represents Telegram MTProto FloodWaitError with required wait seconds."""

    def __init__(self, seconds: int) -> None:
        super().__init__(f"Telegram FloodWaitError: wait {seconds} seconds")
        self.seconds = seconds


class ITelegramClientAdapter(Protocol):
    def resolve_channel(self, handle_or_url: str) -> ResolvedChannelDto: ...
    def fetch_messages_since(
        self, channel_id: str, handle: str, min_message_id: int
    ) -> list[RawTelegramPostDto]: ...
    def fetch_messages_backfill(
        self, channel_id: str, handle: str, days: int = 7
    ) -> list[RawTelegramPostDto]: ...
    def check_messages_exist(
        self, channel_id: str, handle: str, message_ids: list[int]
    ) -> set[int]: ...


def _clean_channel_handle(raw_input: str) -> str:
    """Extracts bare username from @handle or t.me/username link."""
    val = raw_input.strip()
    val = re.sub(r"^(?:https?://)?(?:www\.)?t\.me/", "", val)
    val = val.lstrip("@").rstrip("/")
    if "/" in val:
        val = val.split("/")[0]
    return val


def _guess_language_from_text(text: str) -> str:
    """Quick rule-based language heuristic for Romanian vs Russian."""
    if not text:
        return "RO"
    has_cyrillic = bool(re.search(r"[\u0400-\u04FF]", text))
    has_romanian_chars = bool(re.search(r"[ăâîșțĂÂÎȘȚ]", text, re.IGNORECASE))
    if has_cyrillic and has_romanian_chars:
        return "MIXED"
    if has_cyrillic:
        return "RU"
    return "RO"


class FakeTelegramClientAdapter:
    """Deterministic Telegram client adapter for tests and CI without external network."""

    def __init__(
        self,
        channel_posts: dict[str, list[RawTelegramPostDto]] | None = None,
        flood_wait_once_channels: dict[str, int] | None = None,
        existing_message_ids: dict[str, set[int]] | None = None,
    ) -> None:
        self._posts = channel_posts if channel_posts is not None else self._default_posts()
        self._flood_wait_once = dict(flood_wait_once_channels or {})
        self._existing_message_ids = existing_message_ids or {}

    def resolve_channel(self, handle_or_url: str) -> ResolvedChannelDto:
        username = _clean_channel_handle(handle_or_url)
        if not username:
            raise AppError(
                code="INVALID_CHANNEL_HANDLE",
                message="Channel handle or URL cannot be empty.",
                status_code=400,
            )

        lower = username.lower()
        if "private" in lower:
            raise AppError(
                code="PRIVATE_CHANNEL_REJECTED",
                message=f"Channel '@{username}' is private. ScamGuard only monitors public channels.",
                status_code=400,
            )
        if "group" in lower or "chat" in lower:
            raise AppError(
                code="INVALID_CHANNEL_TYPE",
                message=f"'@{username}' is a group chat. ScamGuard only monitors public broadcast channels.",
                status_code=400,
            )
        if "user" in lower:
            raise AppError(
                code="INVALID_CHANNEL_TYPE",
                message=f"'@{username}' is a user profile. ScamGuard only monitors public broadcast channels.",
                status_code=400,
            )

        title = username.replace("_", " ").title()
        lang = "RU" if any(c in lower for c in ["pravda", "balti", "tiraspol", "ru"]) else "RO"
        tg_id = abs(hash(username)) % 100000000 + 1000000000

        return ResolvedChannelDto(
            telegramChannelId=tg_id,
            handle=f"@{username}",
            title=title,
            subscribersCount=15420,
            languageGuess=lang,
            isPublic=True,
        )

    def fetch_messages_since(
        self, channel_id: str, handle: str, min_message_id: int
    ) -> list[RawTelegramPostDto]:
        if channel_id in self._flood_wait_once:
            wait_sec = self._flood_wait_once.pop(channel_id)
            raise FloodWaitError(seconds=wait_sec)

        posts = self._posts.get(channel_id, [])
        return [p for p in posts if p.telegram_message_id > min_message_id]

    def fetch_messages_backfill(
        self, channel_id: str, handle: str, days: int = 7
    ) -> list[RawTelegramPostDto]:
        if channel_id in self._flood_wait_once:
            wait_sec = self._flood_wait_once.pop(channel_id)
            raise FloodWaitError(seconds=wait_sec)

        posts = self._posts.get(channel_id, [])
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result: list[RawTelegramPostDto] = []
        for post in sorted(posts, key=lambda p: p.telegram_message_id):
            try:
                post_dt = datetime.fromisoformat(post.posted_at.replace("Z", "+00:00"))
                if post_dt >= cutoff:
                    result.append(post)
            except Exception:
                result.append(post)
        return result

    def check_messages_exist(
        self, channel_id: str, handle: str, message_ids: list[int]
    ) -> set[int]:
        if channel_id in self._existing_message_ids:
            return set(message_ids).intersection(self._existing_message_ids[channel_id])
        known = {p.telegram_message_id for p in self._posts.get(channel_id, [])}
        return set(message_ids).intersection(known)

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
                    postLink="https://t.me/moldova_azi_info/101",
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
                    isForward=True,
                    forwardSourceName="Moldova Azi Info",
                    postLink="https://t.me/chisinau_express/201",
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
                    postLink="https://t.me/pridnestrovie_pulse/301",
                ),
            ],
        }


class TelethonClientAdapter:
    """Official MTProto client adapter using Telethon for collecting public Telegram channels."""

    def __init__(
        self,
        session_path: str,
        api_id: int,
        api_hash: str,
    ) -> None:
        self._session_path = session_path
        self._api_id = api_id
        self._api_hash = api_hash
        self._client: Any = None

    async def _get_connected_client(self) -> Any:
        try:
            from telethon import TelegramClient
        except ImportError:
            raise AppError(
                code="TELETHON_NOT_INSTALLED",
                message="Telethon is not installed in the environment.",
                status_code=500,
            ) from None

        if self._client is None:
            sess_path = Path(self._session_path).resolve()
            sess_path.parent.mkdir(parents=True, exist_ok=True)
            self._client = TelegramClient(str(sess_path), self._api_id, self._api_hash)

        if not self._client.is_connected():
            await self._client.connect()

        if not await self._client.is_user_authorized():
            raise AppError(
                code="TELEGRAM_UNAUTHORIZED",
                message="Telegram session is not authorized. Run 'python -m app.cli telegram-login' first.",
                status_code=503,
            )
        return self._client

    def resolve_channel(self, handle_or_url: str) -> ResolvedChannelDto:
        return cast(ResolvedChannelDto, _run_async(self._resolve_channel_async(handle_or_url)))

    async def _resolve_channel_async(self, handle_or_url: str) -> ResolvedChannelDto:
        import telethon.errors as tele_errors
        from telethon.tl.types import Channel, Chat, User

        username = _clean_channel_handle(handle_or_url)
        if not username:
            raise AppError(
                code="INVALID_CHANNEL_HANDLE",
                message="Channel handle or URL cannot be empty.",
                status_code=400,
            )

        client = await self._get_connected_client()
        try:
            entity = await client.get_entity(username)
        except tele_errors.FloodWaitError as exc:
            raise FloodWaitError(seconds=exc.seconds) from exc
        except tele_errors.UsernameInvalidError:
            raise AppError(
                code="INVALID_CHANNEL_HANDLE",
                message=f"Telegram handle '@{username}' does not exist.",
                status_code=404,
            ) from None
        except tele_errors.UsernameNotOccupiedError:
            raise AppError(
                code="CHANNEL_NOT_FOUND",
                message=f"No public Telegram entity found for '@{username}'.",
                status_code=404,
            ) from None
        except Exception as exc:
            raise AppError(
                code="CHANNEL_RESOLUTION_FAILED",
                message=f"Failed to resolve channel '@{username}': {exc}",
                status_code=400,
            ) from exc

        if isinstance(entity, User):
            raise AppError(
                code="INVALID_CHANNEL_TYPE",
                message=f"'@{username}' is a private user account. ScamGuard only monitors public broadcast channels.",
                status_code=400,
            )
        if isinstance(entity, Chat) or (isinstance(entity, Channel) and entity.megagroup):
            raise AppError(
                code="INVALID_CHANNEL_TYPE",
                message=f"'@{username}' is a group chat. ScamGuard only monitors public broadcast channels.",
                status_code=400,
            )
        if not isinstance(entity, Channel) or not entity.broadcast:
            raise AppError(
                code="INVALID_CHANNEL_TYPE",
                message=f"'@{username}' is not a broadcast channel.",
                status_code=400,
            )
        if not getattr(entity, "username", None):
            raise AppError(
                code="PRIVATE_CHANNEL_REJECTED",
                message=f"Channel '{entity.title}' is private. ScamGuard only monitors public channels.",
                status_code=400,
            )

        participants = getattr(entity, "participants_count", None) or 0
        title = entity.title or username
        lang_guess = _guess_language_from_text(title)

        return ResolvedChannelDto(
            telegramChannelId=entity.id,
            handle=f"@{entity.username}",
            title=title,
            subscribersCount=participants,
            languageGuess=lang_guess,
            isPublic=True,
        )

    def fetch_messages_since(
        self, channel_id: str, handle: str, min_message_id: int
    ) -> list[RawTelegramPostDto]:
        return cast(
            list[RawTelegramPostDto],
            _run_async(self._fetch_messages_since_async(channel_id, handle, min_message_id)),
        )

    async def _fetch_messages_since_async(
        self, channel_id: str, handle: str, min_message_id: int
    ) -> list[RawTelegramPostDto]:
        import telethon.errors as tele_errors

        username = _clean_channel_handle(handle)
        client = await self._get_connected_client()
        raw_msgs = []
        try:
            async for message in client.iter_messages(username, min_id=min_message_id, reverse=True):
                raw_msgs.append(message)
        except tele_errors.FloodWaitError as exc:
            raise FloodWaitError(seconds=exc.seconds) from exc
        except Exception as exc:
            logger.error(f"Error fetching new messages for {handle}: {exc}")
            raise

        return self._process_telethon_messages(channel_id, username, raw_msgs)

    def fetch_messages_backfill(
        self, channel_id: str, handle: str, days: int = 7
    ) -> list[RawTelegramPostDto]:
        return cast(
            list[RawTelegramPostDto],
            _run_async(self._fetch_messages_backfill_async(channel_id, handle, days)),
        )

    async def _fetch_messages_backfill_async(
        self, channel_id: str, handle: str, days: int = 7
    ) -> list[RawTelegramPostDto]:
        import telethon.errors as tele_errors

        username = _clean_channel_handle(handle)
        client = await self._get_connected_client()
        cutoff = datetime.now(UTC) - timedelta(days=days)
        raw_msgs = []

        try:
            async for message in client.iter_messages(username, offset_date=cutoff, reverse=True):
                raw_msgs.append(message)
                if len(raw_msgs) % 100 == 0:
                    await asyncio.sleep(0.3)
        except tele_errors.FloodWaitError as exc:
            raise FloodWaitError(seconds=exc.seconds) from exc
        except Exception as exc:
            logger.error(f"Error backfilling messages for {handle}: {exc}")
            raise

        return self._process_telethon_messages(channel_id, username, raw_msgs)

    def check_messages_exist(
        self, channel_id: str, handle: str, message_ids: list[int]
    ) -> set[int]:
        return cast(
            set[int],
            _run_async(self._check_messages_exist_async(channel_id, handle, message_ids)),
        )

    async def _check_messages_exist_async(
        self, channel_id: str, handle: str, message_ids: list[int]
    ) -> set[int]:
        import telethon.errors as tele_errors

        if not message_ids:
            return set()
        username = _clean_channel_handle(handle)
        client = await self._get_connected_client()
        existing_ids: set[int] = set()

        try:
            messages = await client.get_messages(username, ids=message_ids)
            for msg in messages:
                if msg is not None and getattr(msg, "id", None) is not None:
                    if not getattr(msg, "empty", False):
                        existing_ids.add(msg.id)
        except tele_errors.FloodWaitError as exc:
            raise FloodWaitError(seconds=exc.seconds) from exc
        except Exception as exc:
            logger.error(f"Error checking deleted messages for {handle}: {exc}")

        return existing_ids

    def _process_telethon_messages(
        self, channel_id: str, username: str, tele_messages: list[Any]
    ) -> list[RawTelegramPostDto]:
        """Groups albums, extracts captions/text, media flags, forwards, and links."""
        albums: dict[int, list[Any]] = {}
        single_msgs: list[Any] = []

        for msg in tele_messages:
            if getattr(msg, "grouped_id", None):
                albums.setdefault(msg.grouped_id, []).append(msg)
            else:
                single_msgs.append(msg)

        results: list[RawTelegramPostDto] = []

        for msg in single_msgs:
            post = self._telethon_msg_to_dto(channel_id, username, msg)
            results.append(post)

        for grouped_id, items in albums.items():
            items_sorted = sorted(items, key=lambda m: (not bool(m.message), m.id))
            primary = items_sorted[0]
            caption = primary.message or ""
            has_media = any(bool(m.media) for m in items)
            media_types = []
            for m in items:
                m_type = self._get_media_type(m)
                if m_type and m_type not in media_types:
                    media_types.append(m_type)

            edit_date_str = (
                primary.edit_date.astimezone(UTC).isoformat()
                if getattr(primary, "edit_date", None)
                else None
            )
            posted_at_str = (
                primary.date.astimezone(UTC).isoformat()
                if getattr(primary, "date", None)
                else datetime.now(UTC).isoformat()
            )

            is_fwd, fwd_from, fwd_id, fwd_name, fwd_date = self._extract_forward_info(primary)

            results.append(
                RawTelegramPostDto(
                    channelId=channel_id,
                    telegramMessageId=primary.id,
                    rawText=caption,
                    postedAt=posted_at_str,
                    forwardedFrom=fwd_from,
                    viewCount=getattr(primary, "views", 0) or 0,
                    hasMedia=has_media,
                    mediaType="album" if len(items) > 1 else (media_types[0] if media_types else None),
                    forwards=getattr(primary, "forwards", 0) or 0,
                    editDate=edit_date_str,
                    groupedId=str(grouped_id),
                    isForward=is_fwd,
                    forwardSourceChannelId=fwd_id,
                    forwardSourceName=fwd_name,
                    forwardSourceDate=fwd_date,
                    replyToId=getattr(getattr(primary, "reply_to", None), "reply_to_msg_id", None),
                    postLink=f"https://t.me/{username}/{primary.id}",
                )
            )

        return sorted(results, key=lambda p: p.telegram_message_id)

    def _telethon_msg_to_dto(
        self, channel_id: str, username: str, msg: Any
    ) -> RawTelegramPostDto:
        text = getattr(msg, "message", "") or ""
        has_media = bool(getattr(msg, "media", None))
        media_type = self._get_media_type(msg)

        edit_date_str = (
            msg.edit_date.astimezone(UTC).isoformat()
            if getattr(msg, "edit_date", None)
            else None
        )
        posted_at_str = (
            msg.date.astimezone(UTC).isoformat()
            if getattr(msg, "date", None)
            else datetime.now(UTC).isoformat()
        )

        is_fwd, fwd_from, fwd_id, fwd_name, fwd_date = self._extract_forward_info(msg)

        return RawTelegramPostDto(
            channelId=channel_id,
            telegramMessageId=msg.id,
            rawText=text,
            postedAt=posted_at_str,
            forwardedFrom=fwd_from,
            viewCount=getattr(msg, "views", 0) or 0,
            hasMedia=has_media,
            mediaType=media_type,
            forwards=getattr(msg, "forwards", 0) or 0,
            editDate=edit_date_str,
            groupedId=str(msg.grouped_id) if getattr(msg, "grouped_id", None) else None,
            isForward=is_fwd,
            forwardSourceChannelId=fwd_id,
            forwardSourceName=fwd_name,
            forwardSourceDate=fwd_date,
            replyToId=getattr(getattr(msg, "reply_to", None), "reply_to_msg_id", None),
            postLink=f"https://t.me/{username}/{msg.id}",
        )

    @staticmethod
    def _get_media_type(msg: Any) -> str | None:
        media = getattr(msg, "media", None)
        if not media:
            return None
        media_class = media.__class__.__name__.lower()
        if "photo" in media_class:
            return "photo"
        if "document" in media_class:
            doc = getattr(media, "document", None)
            mime = getattr(doc, "mime_type", "") if doc else ""
            if "video" in mime:
                return "video"
            if "audio" in mime:
                return "audio"
            return "document"
        if "video" in media_class:
            return "video"
        return "media"

    @staticmethod
    def _extract_forward_info(msg: object) -> tuple[bool, str | None, str | None, str | None, str | None]:
        fwd = getattr(msg, "fwd_from", None)
        if not fwd:
            return False, None, None, None, None

        is_forward = True
        fwd_from = None
        fwd_id = None
        fwd_name = getattr(fwd, "from_name", None)
        fwd_date = (
            fwd.date.astimezone(UTC).isoformat()
            if getattr(fwd, "date", None)
            else None
        )

        from_id = getattr(fwd, "from_id", None)
        if from_id:
            channel_id = getattr(from_id, "channel_id", None)
            if channel_id:
                fwd_id = str(channel_id)
                fwd_from = f"channel:{channel_id}"

        if not fwd_from and fwd_name:
            fwd_from = fwd_name

        return is_forward, fwd_from, fwd_id, fwd_name, fwd_date
