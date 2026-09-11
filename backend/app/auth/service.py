from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, create_refresh_token, decode_refresh_token, verify_password
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


def issue_refresh_token(user: User, facility_id: UUID | None = None) -> str:
    return create_refresh_token(user.id, facility_id=facility_id)


def rotate_tokens_from_refresh(db: Session, refresh_token: str) -> tuple[User, UUID | None] | None:
    payload = decode_refresh_token(refresh_token)
    try:
        user_id = UUID(payload["sub"])
        facility_id = UUID(payload["facility_id"]) if payload.get("facility_id") else None
    except (ValueError, TypeError):
        return None

    user = db.get(User, user_id)
    if user is None or user.status != "ACTIVE":
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
            return None

    return user, facility_id
