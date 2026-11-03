"""DTOs for authentication, RBAC roles, and versioned admin parameters."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UserRole = Literal["visitor", "journalist", "admin"]


class AuthUserDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User work or newsroom email")
    full_name: str = Field(..., alias="fullName", description="Display full name")
    organization: str = Field(..., description="Newsroom or research organization")
    role: UserRole = Field(..., description="RBAC role: visitor, journalist, or admin")
    account_age_days: int = Field(
        default=0,
        alias="accountAgeDays",
        description="Account age in days for NFR-10 export quota calculation",
    )


class RegisterInputDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    full_name: str = Field(..., alias="fullName")
    email: str
    organization: str = Field(default="Independent Researcher")
    password: str


class LoginInputDto(BaseModel):
    email: str
    password: str


class RefreshTokenInputDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    refresh_token: str = Field(..., alias="refreshToken")


class AuthSessionDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")
    user: AuthUserDto


class SystemParametersDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    parameter_version: str = Field(..., alias="parameterVersion")
    similarity_threshold: float = Field(..., alias="similarityThreshold")
    time_window_minutes: int = Field(..., alias="timeWindowMinutes")
    collection_interval_minutes: int = Field(..., alias="collectionIntervalMinutes")
    min_cluster_channels: int = Field(..., alias="minClusterChannels")
    updated_at: str = Field(..., alias="updatedAt")
    updated_by: str = Field(..., alias="updatedBy")


class UpdateSystemParametersInputDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    similarity_threshold: float = Field(..., alias="similarityThreshold")
    time_window_minutes: int = Field(..., alias="timeWindowMinutes")
    collection_interval_minutes: int = Field(..., alias="collectionIntervalMinutes")
    min_cluster_channels: int = Field(..., alias="minClusterChannels")
