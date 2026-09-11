from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.models import RefreshSession
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.config import settings
from app.rbac.models import Staff, User


def authenticate_user(db: Session, username: str, password: str) -> tuple[User, list[Staff]] | None:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or user.status != "ACTIVE" or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None

    staff = list(
        db.scalars(
            select(Staff).where(Staff.person_id == user.person_id, Staff.status == "ACTIVE")
        )
    )
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return user, staff


def issue_access_token(user: User, facility_id: UUID | None = None) -> str:
    return create_access_token(user.id, facility_id=facility_id)


def issue_refresh_token(db: Session, user: User, facility_id: UUID | None = None) -> str:
    session_id = uuid4()
    family_id = uuid4()
    token = create_refresh_token(user.id, facility_id=facility_id, jti=session_id, family_id=family_id)
    now = datetime.now(timezone.utc)
    db.add(
        RefreshSession(
            id=session_id,
            family_id=family_id,
            user_id=user.id,
            facility_id=facility_id,
            token_hash=hash_refresh_token(token),
            expires_at=now + timedelta(days=settings.refresh_token_days),
        )
    )
    db.commit()
    return token


def rotate_tokens_from_refresh(db: Session, refresh_token: str) -> tuple[User, UUID | None, str] | None:
    payload = decode_refresh_token(refresh_token)
    try:
        user_id = UUID(payload["sub"])
        facility_id = UUID(payload["facility_id"]) if payload.get("facility_id") else None
        session_id = UUID(payload["jti"])
        family_id = UUID(payload["family_id"])
    except (ValueError, TypeError):
        return None

    now = datetime.now(timezone.utc)
    session = db.scalar(
        select(RefreshSession)
        .where(
            RefreshSession.id == session_id,
            RefreshSession.family_id == family_id,
            RefreshSession.token_hash == hash_refresh_token(refresh_token),
        )
        .with_for_update()
    )
    if session is None:
        return None

    if session.revoked_at is not None:
        db.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == family_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        return None

    if session.expires_at <= now:
        session.revoked_at = now
        db.commit()
        return None

    user = db.get(User, user_id)
    if user is None or user.status != "ACTIVE" or session.user_id != user.id:
        session.revoked_at = now
        db.commit()
        return None

    if facility_id != session.facility_id:
        session.revoked_at = now
        db.commit()
        return None

    if facility_id is not None:
        staff = db.scalar(
            select(Staff.id).where(
                Staff.person_id == user.person_id,
                Staff.facility_id == facility_id,
                Staff.status == "ACTIVE",
            )
        )
        if staff is None:
            session.revoked_at = now
            db.commit()
            return None

    new_session_id = uuid4()
    new_token = create_refresh_token(
        user.id,
        facility_id=facility_id,
        jti=new_session_id,
        family_id=family_id,
    )
    db.add(
        RefreshSession(
            id=new_session_id,
            family_id=family_id,
            user_id=user.id,
            facility_id=facility_id,
            token_hash=hash_refresh_token(new_token),
            expires_at=now + timedelta(days=settings.refresh_token_days),
        )
    )
    session.revoked_at = now
    session.replaced_by_id = new_session_id
    session.last_used_at = now
    db.commit()
    return user, facility_id, new_token


def revoke_refresh_token(db: Session, refresh_token: str) -> bool:
    try:
        payload = decode_refresh_token(refresh_token)
        session_id = UUID(payload["jti"])
    except (ValueError, TypeError):
        return False

    session = db.scalar(
        select(RefreshSession).where(
            RefreshSession.id == session_id,
            RefreshSession.token_hash == hash_refresh_token(refresh_token),
        )
    )
    if session is None or session.revoked_at is not None:
        return False
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return True
