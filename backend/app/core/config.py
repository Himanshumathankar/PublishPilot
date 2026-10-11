from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TWPublisher API"
    app_env: str = "development"
    app_secret_key: str = "development-only-secret-key-change-me"
    app_username: str = "admin"
    app_password: str = "change-me"
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+asyncpg://article_publisher:change-me@localhost:5432/article_publisher"
    )
    backend_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    max_upload_size_mb: int = Field(default=25, ge=1, le=100)
    max_docx_uncompressed_mb: int = Field(default=200, ge=10, le=500)
    wordpress_media_max_mb: int = Field(default=1, ge=1, le=100)
    article_storage_path: str = "/app/.data"
    log_level: str = "INFO"
    wordpress_base_url: str | None = None
    wordpress_username: str | None = None
    wordpress_application_password: str | None = None
    rank_math_endpoint: str | None = None
    google_application_credentials: str | None = None

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("app_secret_key")
    @classmethod
    def validate_secret(cls, value: str, info) -> str:
        if info.data.get("app_env") == "production" and (
            len(value) < 32 or value == "development-only-secret-key-change-me"
        ):
            raise ValueError("APP_SECRET_KEY must be a unique value of at least 32 characters")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
