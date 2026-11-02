import pytest

from app.api.routes.admin_routes import get_system_parameters, update_system_parameters
from app.api.routes.auth_routes import (
    get_me,
    login_user,
    logout_user,
    refresh_user_token,
    register_user,
)
from app.core.errors import AppError
from app.core.security import LoginRateLimiter, PasswordHasher, TokenManager
from app.db.database import DatabaseManager
from app.dtos.auth_dto import (
    LoginInputDto,
    RefreshTokenInputDto,
    RegisterInputDto,
    UpdateSystemParametersInputDto,
)
from app.main import create_app
from app.repositories.user_repository import SqliteParameterRepository, SqliteUserRepository
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService


def _build_services() -> tuple[AuthService, AdminService]:
    db_manager = DatabaseManager(":memory:")
    hasher = PasswordHasher(iterations=1_000)
    token_manager = TokenManager(secret_key="test-secret-key")
    rate_limiter = LoginRateLimiter(max_attempts=5)
    user_repo = SqliteUserRepository(db_manager=db_manager, hasher=hasher)
    param_repo = SqliteParameterRepository(db_manager=db_manager)
    auth_service = AuthService(
        user_repo=user_repo,
        hasher=hasher,
        token_manager=token_manager,
        rate_limiter=rate_limiter,
    )
    admin_service = AdminService(param_repo=param_repo)
    return auth_service, admin_service


def test_registration_password_rules_and_duplicate_protection() -> None:
    auth_service, _ = _build_services()

    # Reject weak password without digits
    with pytest.raises(AppError) as exc_weak:
        register_user(
            payload=RegisterInputDto(
                fullName="Test Researcher",
                email="researcher@news.md",
                organization="News MD",
                password="onlyletters",
            ),
            auth_service=auth_service,
        )
    assert exc_weak.value.status_code == 422
    assert exc_weak.value.code == "WEAK_PASSWORD"

    # Valid registration assigns journalist role and accountAgeDays=0
    session = register_user(
        payload=RegisterInputDto(
            fullName="Maria Researcher",
            email="maria@news.md",
            organization="News MD",
            password="securePassword2026",
        ),
        auth_service=auth_service,
    )
    assert session.user.role == "journalist"
    assert session.user.account_age_days == 0

    # Reject duplicate registration
    with pytest.raises(AppError) as exc_dup:
        register_user(
            payload=RegisterInputDto(
                fullName="Maria Researcher",
                email="maria@news.md",
                organization="News MD",
                password="securePassword2026",
            ),
            auth_service=auth_service,
        )
    assert exc_dup.value.status_code == 409
    assert exc_dup.value.code == "EMAIL_ALREADY_REGISTERED"


def test_login_rate_limiting_refresh_and_logout() -> None:
    auth_service, _ = _build_services()

    # 5 failed login attempts trigger 429 RATE_LIMITED on the 6th attempt
    for _ in range(5):
        with pytest.raises(AppError) as exc_bad:
            login_user(
                payload=LoginInputDto(
                    email="ion.rusu@scamguard.md", password="wrongpassword1"
                ),
                auth_service=auth_service,
            )
        assert exc_bad.value.status_code == 401

    with pytest.raises(AppError) as exc_rate:
        login_user(
            payload=LoginInputDto(
                email="ion.rusu@scamguard.md", password="journalist2026"
            ),
            auth_service=auth_service,
        )
    assert exc_rate.value.status_code == 429
    assert exc_rate.value.code == "RATE_LIMITED"

    # Admin login succeeds, refresh rotates tokens, and logout revokes access token
    admin_session = login_user(
        payload=LoginInputDto(
            email="elena.botnari@scamguard.md", password="scamguard2026"
        ),
        auth_service=auth_service,
    )
    assert admin_session.user.role == "admin"

    me = get_me(token=admin_session.access_token, auth_service=auth_service)
    assert me.email == "elena.botnari@scamguard.md"

    refreshed = refresh_user_token(
        payload=RefreshTokenInputDto(refreshToken=admin_session.refresh_token),
        auth_service=auth_service,
    )
    assert refreshed.access_token != admin_session.access_token

    logout_user(token=refreshed.access_token, auth_service=auth_service)
    with pytest.raises(AppError) as exc_revoked:
        get_me(token=refreshed.access_token, auth_service=auth_service)
    assert exc_revoked.value.status_code == 401
    assert exc_revoked.value.code == "TOKEN_REVOKED"


def test_rbac_enforcement_across_visitor_journalist_and_admin_roles() -> None:
    auth_service, admin_service = _build_services()

    # 1. Visitor (no token) is rejected with 401 UNAUTHORIZED
    with pytest.raises(AppError) as exc_visitor:
        get_system_parameters(
            token=None, auth_service=auth_service, admin_service=admin_service
        )
    assert exc_visitor.value.status_code == 401

    # 2. Journalist can view parameters but is rejected with 403 FORBIDDEN on update
    journalist_session = login_user(
        payload=LoginInputDto(
            email="ion.rusu@scamguard.md", password="journalist2026"
        ),
        auth_service=auth_service,
    )
    params = get_system_parameters(
        token=journalist_session.access_token,
        auth_service=auth_service,
        admin_service=admin_service,
    )
    assert params.parameter_version == "v1.4"

    with pytest.raises(AppError) as exc_forbidden:
        update_system_parameters(
            payload=UpdateSystemParametersInputDto(
                similarityThreshold=0.85,
                timeWindowMinutes=45,
                collectionIntervalMinutes=5,
                minClusterChannels=3,
            ),
            token=journalist_session.access_token,
            auth_service=auth_service,
            admin_service=admin_service,
        )
    assert exc_forbidden.value.status_code == 403
    assert exc_forbidden.value.code == "FORBIDDEN"

    # 3. Admin can update parameters (bumps v1.4 -> v1.5) and NFR-01 rejects interval > 10
    admin_session = login_user(
        payload=LoginInputDto(
            email="elena.botnari@scamguard.md", password="scamguard2026"
        ),
        auth_service=auth_service,
    )

    with pytest.raises(AppError) as exc_interval:
        update_system_parameters(
            payload=UpdateSystemParametersInputDto(
                similarityThreshold=0.85,
                timeWindowMinutes=45,
                collectionIntervalMinutes=15,
                minClusterChannels=3,
            ),
            token=admin_session.access_token,
            auth_service=auth_service,
            admin_service=admin_service,
        )
    assert exc_interval.value.status_code == 422
    assert exc_interval.value.code == "INVALID_COLLECTION_INTERVAL"

    updated = update_system_parameters(
        payload=UpdateSystemParametersInputDto(
            similarityThreshold=0.86,
            timeWindowMinutes=45,
            collectionIntervalMinutes=8,
            minClusterChannels=4,
        ),
        token=admin_session.access_token,
        auth_service=auth_service,
        admin_service=admin_service,
    )
    assert updated.parameter_version == "v1.5"
    assert updated.collection_interval_minutes == 8

    # OpenAPI schema includes all auth and admin routes
    openapi_paths = create_app().openapi()["paths"]
    assert "/api/v1/auth/register" in openapi_paths
    assert "/api/v1/auth/login" in openapi_paths
    assert "/api/v1/auth/refresh" in openapi_paths
    assert "/api/v1/auth/logout" in openapi_paths
    assert "/api/v1/auth/me" in openapi_paths
    assert "/api/v1/admin/parameters" in openapi_paths

