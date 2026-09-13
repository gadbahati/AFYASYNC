from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from app.config import Settings, settings


def test_access_token_rejects_refresh_token() -> None:
    token = create_refresh_token(uuid4())
    with pytest.raises(HTTPException, match="INVALID_TOKEN"):
        decode_access_token(token)


def test_refresh_token_requires_refresh_claims() -> None:
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "type": "refresh",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(HTTPException, match="INVALID_REFRESH_TOKEN"):
        decode_refresh_token(token)


def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(environment="production", jwt_secret="change-this-development-secret")


def test_production_requires_long_jwt_secret() -> None:
    with pytest.raises(ValueError, match="32 characters"):
        Settings(environment="production", jwt_secret="too-short")


def test_access_token_contains_facility_scope() -> None:
    facility_id = uuid4()
    payload = jwt.decode(
        create_access_token(uuid4(), facility_id=facility_id),
        options={"verify_signature": False},
    )
    assert payload["facility_id"] == str(facility_id)
    assert payload["type"] == "access"
