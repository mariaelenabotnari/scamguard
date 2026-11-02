"""Dependency injection wiring for services and repositories."""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.db.database import DatabaseManager, get_database_manager
from app.services.health_service import HealthService, IHealthService

SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[DatabaseManager, Depends(get_database_manager)]


def get_health_service(settings: SettingsDep, db_manager: DatabaseDep) -> IHealthService:
    return HealthService(settings=settings, db_manager=db_manager)


HealthServiceDep = Annotated[IHealthService, Depends(get_health_service)]
