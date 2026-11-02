"""Dependency injection wiring for services and repositories."""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.health_service import HealthService, IHealthService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_health_service(settings: SettingsDep) -> IHealthService:
    return HealthService(settings=settings)


HealthServiceDep = Annotated[IHealthService, Depends(get_health_service)]
