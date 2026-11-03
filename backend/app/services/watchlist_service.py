"""Service layer for Telegram channel watchlist CRUD, validation, and pagination."""

from typing import Protocol

from app.core.errors import AppError
from app.dtos.watchlist_dto import (
    AddWatchlistChannelInputDto,
    PaginatedWatchlistResponseDto,
    WatchlistChannelDto,
    WatchlistStatus,
    normalize_telegram_handle,
)
from app.repositories.watchlist_repository import IWatchlistRepository


class IWatchlistService(Protocol):
    def list_channels(
        self, page: int = 1, page_size: int = 50
    ) -> PaginatedWatchlistResponseDto: ...
    def add_channel(
        self, payload: AddWatchlistChannelInputDto, added_by: str
    ) -> WatchlistChannelDto: ...
    def toggle_status(self, channel_id: str) -> WatchlistChannelDto: ...
    def remove_channel(self, channel_id: str) -> None: ...


class WatchlistService:
    """Enforces Telegram handle validation, duplicate protection, and 300+ channel pagination."""

    def __init__(self, repo: IWatchlistRepository) -> None:
        self._repo = repo

    def list_channels(self, page: int = 1, page_size: int = 50) -> PaginatedWatchlistResponseDto:
        safe_page = max(1, page)
        safe_size = min(max(1, page_size), 500)
        items, total = self._repo.list_paginated(page=safe_page, page_size=safe_size)
        return PaginatedWatchlistResponseDto(
            items=items,
            total=total,
            page=safe_page,
            pageSize=safe_size,
        )

    def add_channel(
        self, payload: AddWatchlistChannelInputDto, added_by: str
    ) -> WatchlistChannelDto:
        normalized = normalize_telegram_handle(payload.handle_or_url)
        if not normalized:
            raise AppError(
                code="INVALID_TELEGRAM_HANDLE",
                message=(
                    "Invalid Telegram username. Use @channel_name or "
                    "https://t.me/channel_name (5–32 alphanumeric/underscore characters)."
                ),
                status_code=422,
            )

        existing = self._repo.get_by_handle(normalized)
        if existing is not None:
            raise AppError(
                code="DUPLICATE_CHANNEL",
                message=f"Channel {normalized} is already on the watch list.",
                status_code=409,
            )

        channel_id = f"ch-{normalized[1:].lower()}"
        display_title = payload.title.strip() or normalized
        return self._repo.create_channel(
            channel_id=channel_id,
            handle=normalized,
            title=display_title,
            language=payload.language,
            added_by=added_by,
        )

    def toggle_status(self, channel_id: str) -> WatchlistChannelDto:
        existing = self._repo.get_by_id(channel_id)
        if existing is None:
            raise AppError(
                code="CHANNEL_NOT_FOUND",
                message=f"Channel '{channel_id}' was not found on the watch list.",
                status_code=404,
            )
        next_status: WatchlistStatus = "paused" if existing.status == "active" else "active"
        updated = self._repo.update_status(channel_id=channel_id, status=next_status)
        if updated is None:
            raise AppError(
                code="CHANNEL_NOT_FOUND",
                message=f"Channel '{channel_id}' was not found on the watch list.",
                status_code=404,
            )
        return updated

    def remove_channel(self, channel_id: str) -> None:
        deleted = self._repo.delete_channel(channel_id)
        if not deleted:
            raise AppError(
                code="CHANNEL_NOT_FOUND",
                message=f"Channel '{channel_id}' was not found on the watch list.",
                status_code=404,
            )
