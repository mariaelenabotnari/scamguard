"""DTOs for system health and metadata endpoints."""

from pydantic import BaseModel, Field


class HealthResponseDto(BaseModel):
    status: str = Field(default="ok", description="Current operational status of the service")
    service: str = Field(default="scamguard-backend", description="Service identifier")
    version: str = Field(default="0.1.0", description="API semantic version")

