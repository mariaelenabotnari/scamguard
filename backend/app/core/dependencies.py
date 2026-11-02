"""Dependency injection wiring for services, security primitives, and repositories."""

from typing import Annotated

from fastapi import Depends, Header

from app.core.config import Settings, get_settings
from app.core.security import LoginRateLimiter, PasswordHasher, TokenManager
from app.db.database import DatabaseManager, get_database_manager
from app.repositories.cluster_repository import SqliteClusterRepository
from app.repositories.message_repository import SqliteMessageRepository
from app.repositories.user_repository import SqliteParameterRepository, SqliteUserRepository
from app.repositories.watchlist_repository import SqliteWatchlistRepository
from app.services.admin_service import AdminService, IAdminService
from app.services.auth_service import AuthService, IAuthService
from app.services.clustering_service import ClusteringService, IClusteringService
from app.services.collector_service import (
    FakeTelegramClientAdapter,
    ICollectorService,
    TelegramCollectorService,
)
from app.services.health_service import HealthService, IHealthService
from app.services.narrative_classifier_service import (
    INarrativeClassifierService,
    NarrativeClassifierService,
)
from app.services.similarity_service import SimilarityService
from app.services.text_normaliser import TextNormaliser
from app.services.watchlist_service import IWatchlistService, WatchlistService

SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[DatabaseManager, Depends(get_database_manager)]

_default_hasher = PasswordHasher()
_default_token_manager = TokenManager()
_default_rate_limiter = LoginRateLimiter()


def get_health_service(settings: SettingsDep, db_manager: DatabaseDep) -> IHealthService:
    return HealthService(settings=settings, db_manager=db_manager)


def get_auth_service(db_manager: DatabaseDep) -> IAuthService:
    user_repo = SqliteUserRepository(db_manager=db_manager, hasher=_default_hasher)
    return AuthService(
        user_repo=user_repo,
        hasher=_default_hasher,
        token_manager=_default_token_manager,
        rate_limiter=_default_rate_limiter,
    )


def get_admin_service(db_manager: DatabaseDep) -> IAdminService:
    param_repo = SqliteParameterRepository(db_manager=db_manager)
    return AdminService(param_repo=param_repo)


def get_watchlist_service(db_manager: DatabaseDep) -> IWatchlistService:
    watchlist_repo = SqliteWatchlistRepository(db_manager=db_manager)
    return WatchlistService(repo=watchlist_repo)


def get_collector_service(db_manager: DatabaseDep) -> ICollectorService:
    watchlist_repo = SqliteWatchlistRepository(db_manager=db_manager)
    message_repo = SqliteMessageRepository(db_manager=db_manager)
    normaliser = TextNormaliser()
    client = FakeTelegramClientAdapter()
    return TelegramCollectorService(
        watchlist_repo=watchlist_repo,
        message_repo=message_repo,
        normaliser=normaliser,
        telegram_client=client,
        sleep_fn=lambda _s: None,
    )


def get_clustering_service(db_manager: DatabaseDep) -> IClusteringService:
    message_repo = SqliteMessageRepository(db_manager=db_manager)
    cluster_repo = SqliteClusterRepository(db_manager=db_manager)
    param_repo = SqliteParameterRepository(db_manager=db_manager)
    similarity_service = SimilarityService()
    return ClusteringService(
        message_repo=message_repo,
        cluster_repo=cluster_repo,
        param_repo=param_repo,
        similarity_service=similarity_service,
    )


def get_narrative_classifier_service(
    db_manager: DatabaseDep,
) -> INarrativeClassifierService:
    return NarrativeClassifierService(db_manager=db_manager)


def extract_bearer_token(
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    if not authorization:
        return None
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return authorization.strip()


HealthServiceDep = Annotated[IHealthService, Depends(get_health_service)]
AuthServiceDep = Annotated[IAuthService, Depends(get_auth_service)]
AdminServiceDep = Annotated[IAdminService, Depends(get_admin_service)]
WatchlistServiceDep = Annotated[IWatchlistService, Depends(get_watchlist_service)]
CollectorServiceDep = Annotated[ICollectorService, Depends(get_collector_service)]
ClusteringServiceDep = Annotated[IClusteringService, Depends(get_clustering_service)]
NarrativeClassifierServiceDep = Annotated[
    INarrativeClassifierService, Depends(get_narrative_classifier_service)
]
BearerTokenDep = Annotated[str | None, Depends(extract_bearer_token)]
