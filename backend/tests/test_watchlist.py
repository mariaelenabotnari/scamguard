import pytest

from app.api.routes.auth_routes import login_user
from app.api.routes.watchlist_routes import (
    add_watchlist_channel,
    list_watchlist_channels,
    remove_watchlist_channel,
    toggle_watchlist_channel,
)
from app.core.errors import AppError
from app.core.security import LoginRateLimiter, PasswordHasher, TokenManager
from app.db.database import DatabaseManager
from app.dtos.auth_dto import LoginInputDto
from app.dtos.watchlist_dto import AddWatchlistChannelInputDto, normalize_telegram_handle
from app.main import create_app
from app.repositories.user_repository import SqliteUserRepository
from app.repositories.watchlist_repository import SqliteWatchlistRepository
from app.services.auth_service import AuthService
from app.services.watchlist_service import WatchlistService


def _build_watchlist_services(
    seed_defaults: bool = False,
) -> tuple[AuthService, WatchlistService]:
    db_manager = DatabaseManager(":memory:")
    hasher = PasswordHasher(iterations=1_000)
    token_manager = TokenManager(secret_key="test-watchlist-secret")
    rate_limiter = LoginRateLimiter(max_attempts=5)
    user_repo = SqliteUserRepository(db_manager=db_manager, hasher=hasher)
    watchlist_repo = SqliteWatchlistRepository(db_manager=db_manager, seed_defaults=seed_defaults)
    auth_service = AuthService(
        user_repo=user_repo,
        hasher=hasher,
        token_manager=token_manager,
        rate_limiter=rate_limiter,
    )
    watchlist_service = WatchlistService(repo=watchlist_repo)
    return auth_service, watchlist_service


def test_telegram_handle_normalization_and_validation() -> None:
    assert normalize_telegram_handle("@moldova_news_md") == "@moldova_news_md"
    assert normalize_telegram_handle("https://t.me/chisinau_alert_24/") == "@chisinau_alert_24"
    assert normalize_telegram_handle("t.me/balti_monitor") == "@balti_monitor"
    assert normalize_telegram_handle("bad") is None
    assert normalize_telegram_handle("https://example.com/channel") is None


def test_watchlist_crud_duplicate_protection_and_rbac() -> None:
    auth_service, watchlist_service = _build_watchlist_services(seed_defaults=False)

    journalist_session = login_user(
        payload=LoginInputDto(email="ion.rusu@scamguard.md", password="journalist2026"),
        auth_service=auth_service,
    )
    token = journalist_session.access_token

    # Unauthenticated mutation is rejected
    with pytest.raises(AppError) as exc_unauth:
        add_watchlist_channel(
            payload=AddWatchlistChannelInputDto(
                handleOrUrl="@moldova_observer",
                title="Moldova Observer",
                language="RO",
            ),
            token=None,
            auth_service=auth_service,
            watchlist_service=watchlist_service,
        )
    assert exc_unauth.value.status_code == 401

    # Add valid channel via t.me URL
    added = add_watchlist_channel(
        payload=AddWatchlistChannelInputDto(
            handleOrUrl="https://t.me/moldova_observer",
            title="Moldova Observer",
            language="RO",
        ),
        token=token,
        auth_service=auth_service,
        watchlist_service=watchlist_service,
    )
    assert added.handle == "@moldova_observer"
    assert added.status == "active"

    # Duplicate handle is rejected with 409 DUPLICATE_CHANNEL
    with pytest.raises(AppError) as exc_dup:
        add_watchlist_channel(
            payload=AddWatchlistChannelInputDto(
                handleOrUrl="@Moldova_Observer",
                title="Duplicate",
                language="RO",
            ),
            token=token,
            auth_service=auth_service,
            watchlist_service=watchlist_service,
        )
    assert exc_dup.value.status_code == 409
    assert exc_dup.value.code == "DUPLICATE_CHANNEL"

    # Toggle active -> paused -> active
    paused = toggle_watchlist_channel(
        channel_id=added.id,
        token=token,
        auth_service=auth_service,
        watchlist_service=watchlist_service,
    )
    assert paused.status == "paused"

    resumed = toggle_watchlist_channel(
        channel_id=added.id,
        token=token,
        auth_service=auth_service,
        watchlist_service=watchlist_service,
    )
    assert resumed.status == "active"

    # Remove channel
    result = remove_watchlist_channel(
        channel_id=added.id,
        token=token,
        auth_service=auth_service,
        watchlist_service=watchlist_service,
    )
    assert result["status"] == "removed"
    assert list_watchlist_channels(watchlist_service=watchlist_service).total == 0


def test_add_300_channels_and_list_with_pagination() -> None:
    auth_service, watchlist_service = _build_watchlist_services(seed_defaults=False)
    admin_session = login_user(
        payload=LoginInputDto(email="elena.botnari@scamguard.md", password="scamguard2026"),
        auth_service=auth_service,
    )
    token = admin_session.access_token

    for idx in range(1, 301):
        add_watchlist_channel(
            payload=AddWatchlistChannelInputDto(
                handleOrUrl=f"@moldova_channel_{idx:03d}",
                title=f"Moldova Channel {idx:03d}",
                language="RO" if idx % 2 == 0 else "RU",
            ),
            token=token,
            auth_service=auth_service,
            watchlist_service=watchlist_service,
        )

    page_1 = list_watchlist_channels(watchlist_service=watchlist_service, page=1, page_size=50)
    page_6 = list_watchlist_channels(watchlist_service=watchlist_service, page=6, page_size=50)
    page_7 = list_watchlist_channels(watchlist_service=watchlist_service, page=7, page_size=50)

    assert page_1.total == 300
    assert len(page_1.items) == 50
    assert len(page_6.items) == 50
    assert len(page_7.items) == 0

    openapi_paths = create_app().openapi()["paths"]
    assert "/api/v1/watchlist" in openapi_paths
    assert "/api/v1/watchlist/{channel_id}/toggle" in openapi_paths
    assert "/api/v1/watchlist/{channel_id}/remove" in openapi_paths
