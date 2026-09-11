from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash

from app.config import settings

password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def hash_refresh_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def _create_token(
    user_id: UUID,
    token_type: str,
    expires_minutes: int,
    facility_id: UUID | None = None,
    jti: UUID | None = None,
    family_id: UUID | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "facility_id": str(facility_id) if facility_id else None,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    if token_type == "refresh":
        payload["jti"] = str(jti or uuid4())
        payload["family_id"] = str(family_id or uuid4())
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID, facility_id: UUID | None = None) -> str:
    return _create_token(user_id, "access", settings.access_token_minutes, facility_id)


def create_refresh_token(
    user_id: UUID,
    facility_id: UUID | None = None,
    jti: UUID | None = None,
    family_id: UUID | None = None,
) -> str:
    return _create_token(
        user_id,
        "refresh",
        settings.refresh_token_days * 24 * 60,
        facility_id,
        jti=jti,
        family_id=family_id,
    )


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_TOKEN",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != "access" or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_TOKEN",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_REFRESH_TOKEN",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if (
        payload.get("type") != "refresh"
        or not payload.get("sub")
        or not payload.get("jti")
        or not payload.get("family_id")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_REFRESH_TOKEN",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
