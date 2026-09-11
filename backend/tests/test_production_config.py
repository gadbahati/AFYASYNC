import pytest
from pydantic import ValidationError

from app.config import Settings, _DEFAULT_JWT_SECRET


def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret=_DEFAULT_JWT_SECRET)


def test_production_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret="too-short-secret")


def test_development_allows_default_jwt_secret() -> None:
    settings = Settings(environment="development", jwt_secret=_DEFAULT_JWT_SECRET)
    assert settings.environment == "development"
