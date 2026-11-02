"""HTTP routes for Telegram channel watchlist CRUD and pagination."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.dependencies import AuthServiceDep, BearerTokenDep, WatchlistServiceDep
from app.dtos.watchlist_dto import (
    AddWatchlistChannelInputDto,
    PaginatedWatchlistResponseDto,
    WatchlistChannelDto,
)

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


@router.get("", response_model=PaginatedWatchlistResponseDto)
def list_watchlist_channels(
    watchlist_service: WatchlistServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500, alias="pageSize")] = 50,
) -> PaginatedWatchlistResponseDto:
    return watchlist_service.list_channels(page=page, page_size=page_size)


@router.post("", response_model=WatchlistChannelDto, status_code=201)
def add_watchlist_channel(
    payload: AddWatchlistChannelInputDto,
    token: BearerTokenDep,
    auth_service: AuthServiceDep,
    watchlist_service: WatchlistServiceDep,
) -> WatchlistChannelDto:
    user = auth_service.require_roles(token, ("journalist", "admin"))
    return watchlist_service.add_channel(payload, added_by=user.email)


@router.post("/{channel_id}/toggle", response_model=WatchlistChannelDto)
def toggle_watchlist_channel(
    channel_id: str,
    token: BearerTokenDep,
    auth_service: AuthServiceDep,
    watchlist_service: WatchlistServiceDep,
) -> WatchlistChannelDto:
    auth_service.require_roles(token, ("journalist", "admin"))
    return watchlist_service.toggle_status(channel_id)


@router.post("/{channel_id}/remove")
def remove_watchlist_channel(
    channel_id: str,
    token: BearerTokenDep,
    auth_service: AuthServiceDep,
    watchlist_service: WatchlistServiceDep,
) -> dict[str, str]:
    auth_service.require_roles(token, ("journalist", "admin"))
    watchlist_service.remove_channel(channel_id)
    return {"status": "removed", "channelId": channel_id}
