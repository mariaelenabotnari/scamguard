"""HTTP routes for health checks."""

from fastapi import APIRouter

from app.core.dependencies import HealthServiceDep
from app.dtos.health_dto import HealthResponseDto

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponseDto)
def get_health(health_service: HealthServiceDep) -> HealthResponseDto:
    return health_service.check_health()
