from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import bearer_scheme, decode_access_token
from app.database import get_db
from app.rbac.models import Staff, StaffRole, Role, Permission, RolePermission, User


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_REQUIRED")

    payload = decode_access_token(credentials.credentials)
    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN") from exc

    user = db.get(User, user_id)
    if user is None or user.status != "ACTIVE":
        raise HTTPException(status_code=401, detail="AUTH_REQUIRED")
    return user


def require_permission(permission_code: str):
    def dependency(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        stmt = (
            select(Permission.id)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(StaffRole, StaffRole.role_id == Role.id)
            .join(Staff, Staff.id == StaffRole.staff_id)
            .where(
                Permission.code == permission_code,
                Staff.person_id == user.person_id,
                Staff.status == "ACTIVE",
                StaffRole.facility_id == Staff.facility_id,
            )
            .limit(1)
        )
        if db.scalar(stmt) is None:
            raise HTTPException(status_code=403, detail="PERMISSION_DENIED")
        return user

    return dependency
