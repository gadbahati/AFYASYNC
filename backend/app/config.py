from functools import lru_cache
import re
from urllib.parse import urlparse

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
    worker_poll_seconds: float = 5.0
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

    @field_validator("worker_poll_seconds")
    @classmethod
    def validate_worker_poll(cls, value: float) -> float:
        if value <= 0 or value > 300:
            raise ValueError("WORKER_POLL_SECONDS must be greater than 0 and at most 300")
        return value

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment == "production":
            secret = self.jwt_secret.strip()
            if not secret or secret == _DEFAULT_JWT_SECRET:
                raise ValueError("JWT_SECRET must be set to a strong non-default value when ENVIRONMENT=production")
            if len(secret) < 32:
                raise ValueError("JWT_SECRET must be at least 32 characters in production")
            if len(set(secret)) < 8 or re.fullmatch(r"(.)\1+", secret):
                raise ValueError("JWT_SECRET is too predictable for production")
            if self.jwt_algorithm != "HS256":
                raise ValueError("JWT_ALGORITHM must be HS256 for the configured shared-secret token implementation")
            parsed_db = urlparse(self.database_url)
            if parsed_db.scheme != "postgresql+psycopg":
                raise ValueError("DATABASE_URL must use the PostgreSQL psycopg driver in production")
            if self.database_url == "postgresql+psycopg://afasync:afasync@localhost:5432/afasync":
                raise ValueError("DATABASE_URL must not use the development database in production")
            origins = self.cors_origin_list()
            if not origins:
                raise ValueError("CORS_ORIGINS must contain at least one trusted browser origin in production")
            for origin in origins:
                parsed = urlparse(origin)
                if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
                    raise ValueError("CORS_ORIGINS must contain only explicit HTTPS origins in production; local development origins are not allowed")
        return self

    def cors_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
