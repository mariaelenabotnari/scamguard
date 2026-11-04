"""Application configuration settings loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Scamguard API"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    database_url: str = Field(
        default="postgresql+psycopg://scamguard:scamguard@localhost:5432/scamguard",
        description="Primary PostgreSQL connection string",
    )
    sqlite_path: str = Field(
        default=":memory:",
        description="Local SQLite fallback path for deterministic unit testing and dev runs",
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    default_parameter_version: str = "v1.4"
    max_collection_interval_minutes: int = 10
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "noreply@scamguard.md"
    smtp_tls: bool = True
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_phone: str | None = None
    telegram_session_path: str = "./sessions/scamguard_collector"
    collection_interval_minutes: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def get_settings() -> Settings:
    return Settings()
