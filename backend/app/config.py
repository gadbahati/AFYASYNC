from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_SECRET = "change-this-development-secret"


class Settings(BaseSettings):
    app_name: str = "AfyaSync API"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://afasync:afasync@localhost:5432/afasync"
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    # Comma-separated browser origins allowed to call the API (empty = no CORS)
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

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

    @field_validator("access_token_minutes", "refresh_token_days")
    @classmethod
    def validate_token_lifetimes(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Token lifetime must be positive")
        return value

    @model_validator(mode="after")
    def reject_insecure_production_secrets(self) -> "Settings":
        if self.environment == "production":
            if not self.jwt_secret or self.jwt_secret == _DEFAULT_JWT_SECRET:
                raise ValueError(
                    "JWT_SECRET must be set to a strong non-default value when ENVIRONMENT=production"
                )
            if len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be at least 32 characters in production")
        return self

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
