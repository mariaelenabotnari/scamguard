"""Dependency injection wiring for services, security primitives, and repositories."""

from pathlib import Path
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
from app.services.alert_service import AlertService, IAlertService
from app.services.auth_service import AuthService, IAuthService
from app.services.clustering_service import ClusteringService, IClusteringService
from app.services.collector_service import (
    FakeTelegramClientAdapter,
    ICollectorService,
    TelegramCollectorService,
    TelethonClientAdapter,
)
from app.services.dashboard_service import DashboardService, IDashboardService
from app.services.email_service import EmailService
from app.services.export_service import ExportService, IExportService
from app.services.health_service import HealthService, IHealthService
from app.services.narrative_classifier_service import (
    INarrativeClassifierService,
    NarrativeClassifierService,
)
from app.services.scoring_service import IScoringService, ScoringService
from app.services.search_service import ISearchService, SearchService
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


def get_auth_service(db_manager: DatabaseDep, settings: SettingsDep) -> IAuthService:
    user_repo = SqliteUserRepository(db_manager=db_manager, hasher=_default_hasher)
    email_service = EmailService(settings=settings)
    return AuthService(
        user_repo=user_repo,
        hasher=_default_hasher,
        token_manager=_default_token_manager,
        rate_limiter=_default_rate_limiter,
        email_service=email_service,
    )


def get_admin_service(db_manager: DatabaseDep) -> IAdminService:
    param_repo = SqliteParameterRepository(db_manager=db_manager)
    return AdminService(param_repo=param_repo)


def get_watchlist_service(db_manager: DatabaseDep) -> IWatchlistService:
    watchlist_repo = SqliteWatchlistRepository(db_manager=db_manager)
    return WatchlistService(repo=watchlist_repo)


def get_collector_service(db_manager: DatabaseDep) -> ICollectorService:
    settings = get_settings()
    watchlist_repo = SqliteWatchlistRepository(db_manager=db_manager)
    message_repo = SqliteMessageRepository(db_manager=db_manager)
    normaliser = TextNormaliser()

    session_file = Path(settings.telegram_session_path).resolve().with_suffix(".session")
    if settings.telegram_api_id and settings.telegram_api_hash and session_file.exists():
        client = TelethonClientAdapter(
            session_path=settings.telegram_session_path,
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
        )
    else:
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


def get_scoring_service(db_manager: DatabaseDep) -> IScoringService:
    return ScoringService(db_manager=db_manager)


def get_alert_service(db_manager: DatabaseDep) -> IAlertService:
    return AlertService(db_manager=db_manager)


def get_search_service(
    db_manager: DatabaseDep,
    scoring_service: Annotated[IScoringService, Depends(get_scoring_service)],
    clustering_service: Annotated[IClusteringService, Depends(get_clustering_service)],
) -> ISearchService:
    return SearchService(
        db_manager=db_manager,
        scoring_service=scoring_service,
        clustering_service=clustering_service,
    )


def get_export_service(
    db_manager: DatabaseDep,
    scoring_service: Annotated[IScoringService, Depends(get_scoring_service)],
    clustering_service: Annotated[IClusteringService, Depends(get_clustering_service)],
) -> IExportService:
    return ExportService(
        db_manager=db_manager,
        scoring_service=scoring_service,
        clustering_service=clustering_service,
    )


def get_dashboard_service(db_manager: DatabaseDep) -> IDashboardService:
    return DashboardService(db_manager=db_manager)


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
ScoringServiceDep = Annotated[IScoringService, Depends(get_scoring_service)]
AlertServiceDep = Annotated[IAlertService, Depends(get_alert_service)]
SearchServiceDep = Annotated[ISearchService, Depends(get_search_service)]
ExportServiceDep = Annotated[IExportService, Depends(get_export_service)]
DashboardServiceDep = Annotated[IDashboardService, Depends(get_dashboard_service)]
BearerTokenDep = Annotated[str | None, Depends(extract_bearer_token)]
