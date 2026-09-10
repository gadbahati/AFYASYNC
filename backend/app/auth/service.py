from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, verify_password
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


def issue_access_token(user: User, facility_id=None) -> str:
    return create_access_token(user.id, facility_id=facility_id)
