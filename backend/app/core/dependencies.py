"""Dependency injection wiring for services, security primitives, and repositories."""

from typing import Annotated

from fastapi import Depends, Header

from app.core.config import Settings, get_settings
from app.core.security import LoginRateLimiter, PasswordHasher, TokenManager
from app.db.database import DatabaseManager, get_database_manager
from app.repositories.user_repository import SqliteParameterRepository, SqliteUserRepository
from app.services.admin_service import AdminService, IAdminService
from app.services.auth_service import AuthService, IAuthService
from app.services.health_service import HealthService, IHealthService

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
BearerTokenDep = Annotated[str | None, Depends(extract_bearer_token)]
