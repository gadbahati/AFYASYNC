from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import bearer_scheme, decode_access_token
from app.database import get_db
from app.facilities.models import Facility
from app.rbac.models import Permission, Role, RolePermission, Staff, StaffRole, User


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), db: Session = Depends(get_db)) -> User:
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


def get_token_payload(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="AUTH_REQUIRED")
    return decode_access_token(credentials.credentials)


def get_facility_context(payload: dict = Depends(get_token_payload), user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UUID:
    raw = payload.get("facility_id")
    if not raw:
        raise HTTPException(status_code=403, detail="FACILITY_CONTEXT_REQUIRED")
    try:
        facility_id = UUID(raw)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=403, detail="INVALID_FACILITY_CONTEXT") from exc
    staff = db.scalar(
        select(Staff)
        .join(Facility, Facility.id == Staff.facility_id)
        .where(
            Staff.person_id == user.person_id,
            Staff.facility_id == facility_id,
            Staff.status == "ACTIVE",
            Facility.status == "ACTIVE",
        )
    )
    if staff is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return facility_id


def require_permission(permission_code: str):
    def dependency(user: User = Depends(get_current_user), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> User:
        stmt = (
            select(Permission.id)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(StaffRole, StaffRole.role_id == Role.id)
            .join(Staff, Staff.id == StaffRole.staff_id)
            .join(Facility, Facility.id == Staff.facility_id)
            .where(
                Permission.code == permission_code,
                Staff.person_id == user.person_id,
                Staff.facility_id == facility_id,
                StaffRole.facility_id == facility_id,
                Staff.status == "ACTIVE",
                Facility.status == "ACTIVE",
            ).limit(1)
        )
        if db.scalar(stmt) is None:
            raise HTTPException(status_code=403, detail="PERMISSION_DENIED")
        return user
    return dependency
