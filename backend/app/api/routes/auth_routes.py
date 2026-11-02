"""HTTP routes for researcher registration, login, token refresh, logout, and profile."""

from fastapi import APIRouter

from app.core.dependencies import AuthServiceDep, BearerTokenDep
from app.dtos.auth_dto import (
    AuthSessionDto,
    AuthUserDto,
    LoginInputDto,
    RefreshTokenInputDto,
    RegisterInputDto,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=AuthSessionDto, status_code=201)
def register_user(
    payload: RegisterInputDto,
    auth_service: AuthServiceDep,
) -> AuthSessionDto:
    return auth_service.register(payload)


@router.post("/login", response_model=AuthSessionDto)
def login_user(
    payload: LoginInputDto,
    auth_service: AuthServiceDep,
) -> AuthSessionDto:
    return auth_service.login(payload)


@router.post("/refresh", response_model=AuthSessionDto)
def refresh_user_token(
    payload: RefreshTokenInputDto,
    auth_service: AuthServiceDep,
) -> AuthSessionDto:
    return auth_service.refresh(payload.refresh_token)


@router.post("/logout")
def logout_user(
    token: BearerTokenDep,
    auth_service: AuthServiceDep,
) -> dict[str, str]:
    if token:
        auth_service.logout(token)
    return {"status": "logged_out"}


@router.get("/me", response_model=AuthUserDto)
def get_me(
    token: BearerTokenDep,
    auth_service: AuthServiceDep,
) -> AuthUserDto:
    return auth_service.require_roles(token, ("journalist", "admin"))

