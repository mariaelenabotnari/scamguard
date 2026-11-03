"""HTTP routes for versioned system parameters protected by RBAC roles."""

from fastapi import APIRouter

from app.core.dependencies import AdminServiceDep, AuthServiceDep, BearerTokenDep
from app.dtos.auth_dto import SystemParametersDto, UpdateSystemParametersInputDto

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/parameters", response_model=SystemParametersDto)
def get_system_parameters(
    token: BearerTokenDep,
    auth_service: AuthServiceDep,
    admin_service: AdminServiceDep,
) -> SystemParametersDto:
    auth_service.require_roles(token, ("journalist", "admin"))
    return admin_service.get_parameters()


@router.post("/parameters", response_model=SystemParametersDto)
def update_system_parameters(
    payload: UpdateSystemParametersInputDto,
    token: BearerTokenDep,
    auth_service: AuthServiceDep,
    admin_service: AdminServiceDep,
) -> SystemParametersDto:
    admin_user = auth_service.require_roles(token, ("admin",))
    return admin_service.update_parameters(payload, updated_by=admin_user.email)
