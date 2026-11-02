"""Authentication and Role-Based Access Control (RBAC) service."""

import secrets
from typing import Protocol

from app.core.errors import AppError
from app.core.security import (
    LoginRateLimiter,
    PasswordHasher,
    TokenManager,
    validate_password_strength,
)
from app.dtos.auth_dto import (
    AuthSessionDto,
    AuthUserDto,
    LoginInputDto,
    RegisterInputDto,
    UserRole,
)
from app.repositories.user_repository import IUserRepository, StoredUserRecord


class IAuthService(Protocol):
    def register(self, payload: RegisterInputDto) -> AuthSessionDto: ...
    def login(self, payload: LoginInputDto) -> AuthSessionDto: ...
    def refresh(self, refresh_token: str) -> AuthSessionDto: ...
    def logout(self, token: str) -> None: ...
    def get_current_user(self, access_token: str) -> AuthUserDto: ...
    def require_roles(
        self, access_token: str | None, allowed_roles: tuple[UserRole, ...]
    ) -> AuthUserDto: ...


class AuthService:
    """Implements registration, login rate limiting, token issuance, and RBAC enforcement."""

    def __init__(
        self,
        user_repo: IUserRepository,
        hasher: PasswordHasher,
        token_manager: TokenManager,
        rate_limiter: LoginRateLimiter,
    ) -> None:
        self._user_repo = user_repo
        self._hasher = hasher
        self._token_manager = token_manager
        self._rate_limiter = rate_limiter

    def register(self, payload: RegisterInputDto) -> AuthSessionDto:
        if not payload.full_name.strip():
            raise AppError(
                code="INVALID_NAME",
                message="Full name is required for researcher registration.",
                status_code=422,
            )
        if "@" not in payload.email:
            raise AppError(
                code="INVALID_EMAIL",
                message="Enter a valid work or newsroom email address.",
                status_code=422,
            )
        validate_password_strength(payload.password)

        existing = self._user_repo.get_by_email(payload.email)
        if existing is not None:
            raise AppError(
                code="EMAIL_ALREADY_REGISTERED",
                message=f"An account with email {payload.email} already exists.",
                status_code=409,
            )

        user_id = f"usr-{secrets.token_hex(6)}"
        password_hash = self._hasher.hash_password(payload.password)
        stored = self._user_repo.create_user(
            user_id=user_id,
            email=payload.email,
            full_name=payload.full_name,
            organization=payload.organization,
            role="journalist",
            password_hash=password_hash,
        )
        return self._build_session(stored, account_age_days=0)

    def login(self, payload: LoginInputDto) -> AuthSessionDto:
        rate_key = payload.email.strip().lower()
        self._rate_limiter.check_allowed(rate_key)

        stored = self._user_repo.get_by_email(payload.email)
        if stored is None or not self._hasher.verify_password(
            payload.password, stored.password_hash
        ):
            self._rate_limiter.record_failure(rate_key)
            raise AppError(
                code="INVALID_CREDENTIALS",
                message="Invalid email or password.",
                status_code=401,
            )

        self._rate_limiter.reset(rate_key)
        account_age = 45 if stored.role == "admin" else 14
        return self._build_session(stored, account_age_days=account_age)

    def refresh(self, refresh_token: str) -> AuthSessionDto:
        claims = self._token_manager.verify_token(refresh_token, expected_type="refresh")
        user_id = str(claims.get("sub", ""))
        stored = self._user_repo.get_by_id(user_id)
        if stored is None:
            raise AppError(
                code="USER_NOT_FOUND",
                message="Account associated with refresh token no longer exists.",
                status_code=401,
            )
        self._token_manager.revoke_token(refresh_token)
        account_age = 45 if stored.role == "admin" else 14
        return self._build_session(stored, account_age_days=account_age)

    def logout(self, token: str) -> None:
        self._token_manager.revoke_token(token)

    def get_current_user(self, access_token: str) -> AuthUserDto:
        claims = self._token_manager.verify_token(access_token, expected_type="access")
        user_id = str(claims.get("sub", ""))
        stored = self._user_repo.get_by_id(user_id)
        if stored is None:
            raise AppError(
                code="USER_NOT_FOUND",
                message="Authenticated user was not found.",
                status_code=401,
            )
        account_age = 45 if stored.role == "admin" else 14
        return self._to_user_dto(stored, account_age_days=account_age)

    def require_roles(
        self, access_token: str | None, allowed_roles: tuple[UserRole, ...]
    ) -> AuthUserDto:
        if not access_token:
            raise AppError(
                code="UNAUTHORIZED",
                message="Authentication token is required.",
                status_code=401,
            )
        user = self.get_current_user(access_token)
        if user.role not in allowed_roles:
            raise AppError(
                code="FORBIDDEN",
                message=f"Role '{user.role}' is not permitted to access this resource.",
                status_code=403,
                details={"required_roles": list(allowed_roles)},
            )
        return user

    def _build_session(
        self, stored: StoredUserRecord, account_age_days: int
    ) -> AuthSessionDto:
        access_token = self._token_manager.create_token(
            user_id=stored.id, role=stored.role, token_type="access", ttl_seconds=3600
        )
        refresh_token = self._token_manager.create_token(
            user_id=stored.id,
            role=stored.role,
            token_type="refresh",
            ttl_seconds=86400 * 7,
        )
        return AuthSessionDto(
            accessToken=access_token,
            refreshToken=refresh_token,
            user=self._to_user_dto(stored, account_age_days=account_age_days),
        )

    @staticmethod
    def _to_user_dto(stored: StoredUserRecord, account_age_days: int) -> AuthUserDto:
        return AuthUserDto(
            id=stored.id,
            email=stored.email,
            fullName=stored.full_name,
            organization=stored.organization,
            role=stored.role,
            accountAgeDays=account_age_days,
        )

