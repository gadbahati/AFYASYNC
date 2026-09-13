from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_SECRET = "change-this-development-secret"
_DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://localhost:5173"


class Settings(BaseSettings):
    app_name: str = "AfyaSync API"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://afasync:afasync@localhost:5432/afasync"
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout_seconds: int = 30
    db_pool_recycle_seconds: int = 1800
    cors_origins: str = _DEFAULT_CORS_ORIGINS

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        url = value.strip()
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and "+psycopg" not in url:
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @field_validator("access_token_minutes", "refresh_token_days", "db_pool_size", "db_max_overflow", "db_pool_timeout_seconds", "db_pool_recycle_seconds")
    @classmethod
    def validate_positive_settings(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Numeric setting must be positive")
        return value

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment == "production":
            if not self.jwt_secret or self.jwt_secret == _DEFAULT_JWT_SECRET:
                raise ValueError("JWT_SECRET must be set to a strong non-default value when ENVIRONMENT=production")
            if len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be at least 32 characters in production")
            origins = self.cors_origin_list()
            if not origins:
                raise ValueError("CORS_ORIGINS must contain at least one trusted browser origin in production")
            if any(origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1") for origin in origins):
                raise ValueError("CORS_ORIGINS must not contain local development origins in production")
        return self

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
