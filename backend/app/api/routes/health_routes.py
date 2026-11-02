"""HTTP routes for health and metadata checks."""

from fastapi import APIRouter

from app.core.dependencies import HealthServiceDep
from app.dtos.health_dto import HealthResponseDto, MetaResponseDto

router = APIRouter(tags=["system"])
v1_system_router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/health", response_model=HealthResponseDto)
def get_health(health_service: HealthServiceDep) -> HealthResponseDto:
    return health_service.check_health()


@v1_system_router.get("/health", response_model=HealthResponseDto)
def get_v1_health(health_service: HealthServiceDep) -> HealthResponseDto:
    return health_service.check_health()


@v1_system_router.get("/meta", response_model=MetaResponseDto)
def get_v1_meta(health_service: HealthServiceDep) -> MetaResponseDto:
    return health_service.get_meta()
