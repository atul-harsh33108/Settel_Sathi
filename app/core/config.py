"""Typed, non-secret application configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "SettleSaathi API"
    environment: str = Field(default="development", validation_alias="SETTLESAATHI_ENV")
    log_level: str = Field(default="INFO", validation_alias="SETTLESAATHI_LOG_LEVEL")
    api_prefix: str = Field(default="/api/v1", validation_alias="SETTLESAATHI_API_PREFIX")
    cors_origins: str = Field(
        default="http://localhost:5173", validation_alias="SETTLESAATHI_CORS_ORIGINS"
    )
    database_url: str = Field(
        default="sqlite:///./data/settlesaathi.db",
        validation_alias="SETTLESAATHI_DATABASE_URL",
    )
    storage_dir: Path = Field(default=Path("storage"), validation_alias="SETTLESAATHI_STORAGE_DIR")
    llm_api_key: str | None = Field(default=None, validation_alias="SETTLESAATHI_LLM_API_KEY")
    llm_model: str | None = Field(default=None, validation_alias="SETTLESAATHI_LLM_MODEL")

    @property
    def allowed_origins(self) -> list[str]:
        """Return normalized development CORS origins."""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached immutable configuration object for the application process."""

    return Settings()
