from datetime import datetime, timedelta, timezone
from uuid import uuid4
import jwt
import pytest
from fastapi import HTTPException
from app.auth.security import create_access_token, create_refresh_token, decode_access_token, decode_refresh_token
from app.config import Settings, settings

_PRODUCTION_DB = "postgresql+psycopg://user:password@db.internal:5432/afasync"

def test_access_token_rejects_refresh_token() -> None:
    token = create_refresh_token(uuid4())
    with pytest.raises(HTTPException, match="INVALID_TOKEN"): decode_access_token(token)

def test_refresh_token_requires_refresh_claims() -> None:
    token = jwt.encode({"sub": str(uuid4()), "type": "refresh", "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    with pytest.raises(HTTPException, match="INVALID_REFRESH_TOKEN"): decode_refresh_token(token)

def _secure_test_secret() -> str:
    return "vR7!qP2#sL9@xC4$mN8%tK6^wF3&zH5*"

def _production(**overrides):
    values = {"environment": "production", "jwt_secret": _secure_test_secret(), "cors_origins": "https://app.example.com", "database_url": _PRODUCTION_DB}
    values.update(overrides)
    return Settings(**values)

def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET"): _production(jwt_secret="change-this-development-secret")

def test_production_requires_long_jwt_secret() -> None:
    with pytest.raises(ValueError, match="32 characters"): _production(jwt_secret="too-short")

def test_production_rejects_predictable_jwt_secret() -> None:
    with pytest.raises(ValueError, match="predictable"): _production(jwt_secret="a" * 32)

def test_production_requires_explicit_cors_origin() -> None:
    with pytest.raises(ValueError, match="CORS_ORIGINS"): _production(cors_origins="")

def test_production_rejects_local_cors_origin() -> None:
    with pytest.raises(ValueError, match="local development origins"): _production(cors_origins="http://localhost:5173")

def test_production_rejects_cors_path() -> None:
    with pytest.raises(ValueError, match="CORS_ORIGINS"): _production(cors_origins="https://app.example.com/path")

def test_production_accepts_trusted_https_cors_origin() -> None:
    configured = _production()
    assert configured.cors_origin_list() == ["https://app.example.com"]

def test_access_token_contains_facility_scope() -> None:
    facility_id = uuid4()
    payload = jwt.decode(create_access_token(uuid4(), facility_id=facility_id), options={"verify_signature": False})
    assert payload["facility_id"] == str(facility_id)
    assert payload["type"] == "access"
