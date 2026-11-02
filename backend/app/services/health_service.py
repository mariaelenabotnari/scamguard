"""Service layer for system health and diagnostics."""

from typing import Protocol

from app.core.config import Settings
from app.dtos.health_dto import HealthResponseDto


class IHealthService(Protocol):
    def check_health(self) -> HealthResponseDto: ...


class HealthService:
    """Concrete implementation of health diagnostics following Single Responsibility Principle."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def check_health(self) -> HealthResponseDto:
        return HealthResponseDto(
            status="ok",
            service="scamguard-backend",
            version=self._settings.app_version,
        )

