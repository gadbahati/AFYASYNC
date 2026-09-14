import pytest
from pydantic import ValidationError

from app.config import Settings, _DEFAULT_JWT_SECRET


def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret=_DEFAULT_JWT_SECRET, cors_origins="https://app.example.com", database_url="postgresql+psycopg://user:password@db.internal:5432/afasync")


def test_production_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret="too-short-secret", cors_origins="https://app.example.com", database_url="postgresql+psycopg://user:password@db.internal:5432/afasync")


def test_production_requires_https_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret="a" * 32, cors_origins="http://app.example.com", database_url="postgresql+psycopg://user:password@db.internal:5432/afasync")


def test_production_rejects_development_database() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret="a" * 32, cors_origins="https://app.example.com", database_url="postgresql+psycopg://afasync:afasync@localhost:5432/afasync")


def test_production_accepts_explicit_secure_configuration() -> None:
    settings = Settings(
        environment="production",
        jwt_secret="a" * 32,
        cors_origins="https://app.example.com/",
        database_url="postgresql+psycopg://user:password@db.internal:5432/afasync",
    )
    assert settings.cors_origin_list() == ["https://app.example.com"]


def test_development_allows_default_configuration() -> None:
    settings = Settings(environment="development", jwt_secret=_DEFAULT_JWT_SECRET)
    assert settings.environment == "development"
