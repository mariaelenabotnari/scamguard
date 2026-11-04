"""DTOs and Telegram handle normalization for channel watchlist management."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WatchlistStatus = Literal["active", "paused"]
ChannelLanguage = Literal["RO", "RU", "MIXED"]

_TELEGRAM_URL_PATTERN = re.compile(r"^(?:https?://)?t\.me/([a-zA-Z0-9_]{5,32})/?$")
_TELEGRAM_HANDLE_PATTERN = re.compile(r"^@([a-zA-Z0-9_]{5,32})$")


def normalize_telegram_handle(raw_input: str) -> str | None:
    """Validates and normalizes a Telegram `@handle` or `https://t.me/handle` URL."""
    trimmed = raw_input.strip()
    url_match = _TELEGRAM_URL_PATTERN.match(trimmed)
    if url_match:
        return f"@{url_match.group(1)}"

    handle_match = _TELEGRAM_HANDLE_PATTERN.match(trimmed)
    if handle_match:
        return f"@{handle_match.group(1)}"

    return None


class WatchlistChannelDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Unique channel identifier")
    handle: str = Field(..., description="Normalized Telegram @handle")
    title: str = Field(..., description="Public channel display title")
    language: ChannelLanguage = Field(default="RO", description="Primary channel language")
    status: WatchlistStatus = Field(default="active", description="Collection status")
    added_by: str = Field(..., alias="addedBy", description="Researcher who added the channel")
    added_at: str = Field(..., alias="addedAt", description="ISO date when channel was added")
    subscribers_count: int = Field(
        default=0, alias="subscribersCount", description="Subscriber count snapshot"
    )
    telegram_channel_id: int | None = Field(
        default=None, alias="telegramChannelId", description="Stable Telegram MTProto channel ID"
    )
    last_collected_at: str | None = Field(
        default=None, alias="lastCollectedAt", description="ISO timestamp of last collection"
    )
    last_error: str | None = Field(
        default=None, alias="lastError", description="Last collection error message if any"
    )


class AddWatchlistChannelInputDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    handle_or_url: str = Field(
        ...,
        alias="handleOrUrl",
        description="Telegram @username or https://t.me/username link",
    )
    title: str = Field(default="", description="Optional channel display title")
    language: ChannelLanguage = Field(default="RO", description="Channel primary language")


class PaginatedWatchlistResponseDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[WatchlistChannelDto]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
