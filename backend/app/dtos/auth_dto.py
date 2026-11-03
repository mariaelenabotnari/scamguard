"""DTOs for authentication, RBAC roles, and versioned admin parameters."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UserRole = Literal["visitor", "journalist", "admin"]


class AuthUserDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User work or newsroom email")
    username: str = Field(default="", description="Unique username")
    full_name: str = Field(..., alias="fullName", description="Display full name")
    organization: str = Field(..., description="Newsroom or research organization")
    role: UserRole = Field(..., description="RBAC role: visitor, journalist, or admin")
    is_verified: bool = Field(default=True, alias="isVerified")
    account_age_days: int = Field(
        default=0,
        alias="accountAgeDays",
        description="Account age in days for NFR-10 export quota calculation",
    )


class RegisterInputDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: str
    password: str
    username: str = Field(default="")
    full_name: str | None = Field(default=None, alias="fullName")
    organization: str = Field(default="Independent Researcher")


class VerifyEmailInputDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: str
    code: str


class SendVerificationCodeInputDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: str


class VerificationResponseDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    email: str
    code: str | None = None
    requires_verification: bool = Field(default=True, alias="requiresVerification")


class LoginInputDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    password: str
    email: str | None = None
    username: str | None = None
    login: str | None = None


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

