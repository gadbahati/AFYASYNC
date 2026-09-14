import pytest
from pydantic import ValidationError

from app.config import _DEFAULT_JWT_SECRET, Settings


def _production(**overrides):
    values = {
        "environment": "production",
        "jwt_secret": "vR7!qP2#sL9@xC4$mN8%tK6^wF3&zH5*",
        "cors_origins": "https://app.example.com",
        "database_url": "postgresql+psycopg://user:password@db.internal:5432/afasync",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_rejects_default_jwt_secret():
    with pytest.raises(ValidationError):
        _production(jwt_secret=_DEFAULT_JWT_SECRET)


def test_production_rejects_short_jwt_secret():
    with pytest.raises(ValidationError):
        _production(jwt_secret="aB3!short")


def test_production_rejects_predictable_jwt_secret():
    with pytest.raises(ValidationError):
        _production(jwt_secret="a" * 32)


def test_production_rejects_non_hs256_algorithm():
    with pytest.raises(ValidationError):
        _production(jwt_algorithm="HS512")


def test_production_requires_psycopg_postgres_database():
    with pytest.raises(ValidationError):
        _production(database_url="sqlite:///afasync.db")


def test_production_rejects_development_database():
    with pytest.raises(ValidationError):
        _production(database_url="postgresql+psycopg://afasync:afasync@localhost:5432/afasync")


def test_production_requires_https_cors_origins():
    with pytest.raises(ValidationError):
        _production(cors_origins="http://app.example.com")


def test_production_rejects_cors_paths_and_queries():
    with pytest.raises(ValidationError):
        _production(cors_origins="https://app.example.com/path")
    with pytest.raises(ValidationError):
        _production(cors_origins="https://app.example.com/?tenant=1")


def test_production_accepts_explicit_secure_configuration():
    configured = _production(cors_origins="https://app.example.com/")
    assert configured.cors_origin_list() == ["https://app.example.com"]
    assert configured.worker_poll_seconds == 5.0


def test_worker_poll_must_be_positive_and_bounded():
    with pytest.raises(ValidationError):
        Settings(worker_poll_seconds=0)
    with pytest.raises(ValidationError):
        Settings(worker_poll_seconds=301)


def test_development_defaults_remain_available():
    configured = Settings(environment="development")
    assert configured.jwt_secret == _DEFAULT_JWT_SECRET
    assert configured.cors_origin_list() == ["http://localhost:3000", "http://localhost:5173"]
