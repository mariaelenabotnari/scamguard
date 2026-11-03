"""Authentication and Role-Based Access Control (RBAC) service."""

import re
import secrets
from datetime import UTC, datetime, timedelta
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
    VerificationResponseDto,
    VerifyEmailInputDto,
)
from app.repositories.user_repository import IUserRepository, StoredUserRecord


class IAuthService(Protocol):
    def register(self, payload: RegisterInputDto) -> VerificationResponseDto: ...
    def verify_email(self, payload: VerifyEmailInputDto) -> AuthSessionDto: ...
    def resend_verification_code(self, email: str) -> VerificationResponseDto: ...
    def login(self, payload: LoginInputDto) -> AuthSessionDto: ...
    def refresh(self, refresh_token: str) -> AuthSessionDto: ...
    def logout(self, token: str) -> None: ...
    def get_current_user(self, access_token: str) -> AuthUserDto: ...
    def require_roles(
        self, access_token: str | None, allowed_roles: tuple[UserRole, ...]
    ) -> AuthUserDto: ...


class AuthService:
    """Implements registration, email verification, login rate limiting, and RBAC enforcement."""

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

    def register(self, payload: RegisterInputDto) -> VerificationResponseDto:
        clean_email = payload.email.strip().lower()
        if "@" not in clean_email or "." not in clean_email.split("@")[-1]:
            raise AppError(
                code="INVALID_EMAIL",
                message="Enter a valid work or newsroom email address.",
                status_code=422,
            )

        raw_username = payload.username.strip() if payload.username else clean_email.split("@")[0]
        if not re.match(r"^[a-zA-Z0-9_]{3,30}$", raw_username):
            raise AppError(
                code="INVALID_USERNAME",
                message="Username must be 3-30 characters (letters, numbers, underscores).",
                status_code=422,
            )

        full_name = (payload.full_name or "").strip() or raw_username
        validate_password_strength(payload.password)

        existing_email = self._user_repo.get_by_email(clean_email)
        if existing_email is not None:
            raise AppError(
                code="EMAIL_ALREADY_REGISTERED",
                message=f"An account with email {clean_email} already exists.",
                status_code=409,
            )

        existing_user = self._user_repo.get_by_username(raw_username)
        if existing_user is not None:
            raise AppError(
                code="USERNAME_ALREADY_TAKEN",
                message=f"Username '{raw_username}' is already in use.",
                status_code=409,
            )

        user_id = f"usr-{secrets.token_hex(6)}"
        password_hash = self._hasher.hash_password(payload.password)
        self._user_repo.create_user(
            user_id=user_id,
            email=clean_email,
            full_name=full_name,
            organization=payload.organization or "Independent Researcher",
            role="journalist",
            password_hash=password_hash,
            username=raw_username,
            is_verified=False,
        )

        code = f"{secrets.randbelow(900000) + 100000:06d}"
        expires_at = (datetime.now(UTC) + timedelta(minutes=15)).isoformat()
        self._user_repo.store_verification_code(clean_email, code, expires_at)

        return VerificationResponseDto(
            message="Verification code sent to your email.",
            email=clean_email,
            code=code,
            requiresVerification=True,
        )

    def verify_email(self, payload: VerifyEmailInputDto) -> AuthSessionDto:
        clean_email = payload.email.strip().lower()
        code_input = payload.code.strip()
        record = self._user_repo.get_verification_code(clean_email)
        if not record:
            raise AppError(
                code="INVALID_VERIFICATION_CODE",
                message="No pending verification code found for this email.",
                status_code=400,
            )

        expected_code, expires_at_iso = record
        if expected_code != code_input:
            raise AppError(
                code="INVALID_VERIFICATION_CODE",
                message="Incorrect verification code. Please check your email or resend a code.",
                status_code=400,
            )

        expires_at = datetime.fromisoformat(expires_at_iso)
        if datetime.now(UTC) > expires_at:
            raise AppError(
                code="VERIFICATION_CODE_EXPIRED",
                message="Verification code has expired. Please request a new code.",
                status_code=400,
            )

        self._user_repo.mark_email_verified(clean_email)
        stored = self._user_repo.get_by_email(clean_email)
        if not stored:
            raise AppError(
                code="USER_NOT_FOUND",
                message="User account not found.",
                status_code=404,
            )
        return self._build_session(stored, account_age_days=0)

    def resend_verification_code(self, email: str) -> VerificationResponseDto:
        clean_email = email.strip().lower()
        stored = self._user_repo.get_by_email(clean_email)
        if not stored:
            raise AppError(
                code="USER_NOT_FOUND",
                message=f"No account found with email {clean_email}.",
                status_code=404,
            )
        if stored.is_verified:
            return VerificationResponseDto(
                message="Account email is already verified.",
                email=clean_email,
                code=None,
                requiresVerification=False,
            )

        code = f"{secrets.randbelow(900000) + 100000:06d}"
        expires_at = (datetime.now(UTC) + timedelta(minutes=15)).isoformat()
        self._user_repo.store_verification_code(clean_email, code, expires_at)
        return VerificationResponseDto(
            message="New verification code sent.",
            email=clean_email,
            code=code,
            requiresVerification=True,
        )

    def login(self, payload: LoginInputDto) -> AuthSessionDto:
        raw_identifier = (
            payload.email
            or payload.username
            or payload.login
            or ""
        ).strip()
        if not raw_identifier:
            raise AppError(
                code="INVALID_CREDENTIALS",
                message="Email or username is required.",
                status_code=422,
            )
        rate_key = raw_identifier.lower()
        self._rate_limiter.check_allowed(rate_key)

        stored = self._user_repo.get_by_identifier(raw_identifier)
        if stored is None or not self._hasher.verify_password(
            payload.password, stored.password_hash
        ):
            self._rate_limiter.record_failure(rate_key)
            raise AppError(
                code="INVALID_CREDENTIALS",
                message="Invalid email/username or password.",
                status_code=401,
            )

        if not stored.is_verified:
            raise AppError(
                code="EMAIL_NOT_VERIFIED",
                message="Please verify your email address to activate your account.",
                status_code=403,
                details={"email": stored.email, "requiresVerification": True},
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

    def _build_session(self, stored: StoredUserRecord, account_age_days: int) -> AuthSessionDto:
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
            username=stored.username,
            fullName=stored.full_name,
            organization=stored.organization,
            role=stored.role,
            isVerified=stored.is_verified,
            accountAgeDays=account_age_days,
        )
