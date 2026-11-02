"""DTOs for system health and metadata endpoints."""

from pydantic import BaseModel, Field


class HealthResponseDto(BaseModel):
    status: str = Field(default="ok", description="Current operational status of the service")
    service: str = Field(default="scamguard-backend", description="Service identifier")
    version: str = Field(default="0.1.0", description="API semantic version")


class MetaResponseDto(BaseModel):
    app_name: str = Field(..., description="Application display name")
    version: str = Field(..., description="API semantic version")
    environment: str = Field(..., description="Runtime environment name")
    api_v1_prefix: str = Field(..., description="Base path for v1 endpoints")
    schema_revision: str = Field(..., description="Current applied database migration revision")
    active_parameter_version: str = Field(
        ..., description="Active versioned coordination parameter set (NFR-13)"
    )
    max_collection_interval_minutes: int = Field(
        ..., description="Maximum allowed collector polling interval in minutes (NFR-01)"
    )
