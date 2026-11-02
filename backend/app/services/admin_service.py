"""Admin parameters service enforcing NFR-01 polling cap and NFR-13 versioned parameters."""

from typing import Protocol

from app.core.errors import AppError
from app.dtos.auth_dto import SystemParametersDto, UpdateSystemParametersInputDto
from app.repositories.user_repository import IParameterRepository


class IAdminService(Protocol):
    def get_parameters(self) -> SystemParametersDto: ...
    def update_parameters(
        self, payload: UpdateSystemParametersInputDto, updated_by: str
    ) -> SystemParametersDto: ...


class AdminService:
    """Validates and bumps immutable system parameter versions (NFR-01, NFR-13)."""

    def __init__(self, param_repo: IParameterRepository) -> None:
        self._param_repo = param_repo

    def get_parameters(self) -> SystemParametersDto:
        return self._param_repo.get_latest()

    def update_parameters(
        self, payload: UpdateSystemParametersInputDto, updated_by: str
    ) -> SystemParametersDto:
        if (
            payload.collection_interval_minutes < 1
            or payload.collection_interval_minutes > 10
        ):
            raise AppError(
                code="INVALID_COLLECTION_INTERVAL",
                message=(
                    "Collection interval must be between 1 and 10 minutes "
                    "(NFR-01 max 10 min polling interval)."
                ),
                status_code=422,
                details={"max_collection_interval_minutes": 10},
            )

        if (
            payload.similarity_threshold < 0.50
            or payload.similarity_threshold > 0.99
        ):
            raise AppError(
                code="INVALID_SIMILARITY_THRESHOLD",
                message="Similarity threshold must be between 0.50 and 0.99.",
                status_code=422,
            )

        if payload.time_window_minutes < 5 or payload.time_window_minutes > 180:
            raise AppError(
                code="INVALID_TIME_WINDOW",
                message="Coordination time window must be between 5 and 180 minutes.",
                status_code=422,
            )

        latest = self._param_repo.get_latest()
        next_version = self._bump_minor_version(latest.parameter_version)
        return self._param_repo.create_version(
            version=next_version,
            similarity_threshold=payload.similarity_threshold,
            time_window_minutes=payload.time_window_minutes,
            collection_interval_minutes=payload.collection_interval_minutes,
            min_cluster_channels=payload.min_cluster_channels,
            updated_by=updated_by,
        )

    @staticmethod
    def _bump_minor_version(current_version: str) -> str:
        cleaned = current_version.strip().removeprefix("v")
        parts = cleaned.split(".")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return f"v{parts[0]}.{int(parts[1]) + 1}"
        return "v1.5"

