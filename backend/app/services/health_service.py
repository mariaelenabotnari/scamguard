"""Service layer for system health and metadata diagnostics."""

from typing import Protocol

from app.core.config import Settings
from app.db.database import DatabaseManager
from app.dtos.health_dto import HealthResponseDto, MetaResponseDto


class IHealthService(Protocol):
    def check_health(self) -> HealthResponseDto: ...
    def get_meta(self) -> MetaResponseDto: ...


class HealthService:
    """Concrete implementation of health and metadata diagnostics."""

    def __init__(self, settings: Settings, db_manager: DatabaseManager) -> None:
        self._settings = settings
        self._db_manager = db_manager

    def check_health(self) -> HealthResponseDto:
        return HealthResponseDto(
            status="ok",
            service="scamguard-backend",
            version=self._settings.app_version,
        )

    def get_meta(self) -> MetaResponseDto:
        revision = self._db_manager.get_current_revision()
        return MetaResponseDto(
            app_name=self._settings.app_name,
            version=self._settings.app_version,
            environment=self._settings.environment,
            api_v1_prefix=self._settings.api_v1_prefix,
            schema_revision=revision,
            active_parameter_version=self._settings.default_parameter_version,
            max_collection_interval_minutes=self._settings.max_collection_interval_minutes,
        )
