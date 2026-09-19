from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import bearer_scheme, decode_access_token
from app.database import get_db
from app.facilities.models import Facility
from app.rbac.models import Permission, Role, RolePermission, Staff, StaffRole, User


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


def get_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="AUTH_REQUIRED")
    return decode_access_token(credentials.credentials)


def require_patient_identity(
    user: User = Depends(get_current_user),
    payload: dict = Depends(get_token_payload),
) -> User:
    """Portal endpoints: user must be linked to a person and must not carry staff facility context.

    Patient access tokens are issued with facility_id=None. A staff token that includes
    a facility_id must not be used to call patient portal APIs.
    """
    if user.person_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PATIENT_IDENTITY_REQUIRED",
        )
    if payload.get("facility_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PATIENT_PORTAL_REQUIRES_PATIENT_TOKEN",
        )
    return user


def _is_system_administrator(db: Session, user: User) -> bool:
    if user.person_id is None:
        return False
    return (
        db.scalar(
            select(StaffRole.staff_id)
            .join(Staff, Staff.id == StaffRole.staff_id)
            .join(Role, Role.id == StaffRole.role_id)
            .where(
                Staff.person_id == user.person_id,
                Staff.status == "ACTIVE",
                Role.name == "System Administrator",
            )
            .limit(1)
        )
        is not None
    )


def get_facility_context(
    payload: dict = Depends(get_token_payload),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UUID:
    raw = payload.get("facility_id")
    if not raw:
        raise HTTPException(status_code=403, detail="FACILITY_CONTEXT_REQUIRED")
    try:
        facility_id = UUID(raw)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=403, detail="INVALID_FACILITY_CONTEXT") from exc

    facility = db.scalar(
        select(Facility).where(Facility.id == facility_id, Facility.status == "ACTIVE").limit(1)
    )
    if facility is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    if _is_system_administrator(db, user):
        return facility_id

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


# Alias used across the codebase
require_facility_context = get_facility_context


def require_permission(permission_code: str):
    def dependency(
        user: User = Depends(get_current_user),
        facility_id: UUID = Depends(get_facility_context),
        db: Session = Depends(get_db),
    ) -> User:
        if _is_system_administrator(db, user):
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
                )
                .limit(1)
            )
        else:
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
                )
                .limit(1)
            )
        if db.scalar(stmt) is None:
            raise HTTPException(status_code=403, detail="PERMISSION_DENIED")
        return user

    return dependency


def require_national_permission(permission_code: str):
    """Require an explicitly assigned permission without creating a facility context."""

    def dependency(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
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
                StaffRole.facility_id == Staff.facility_id,
                Staff.status == "ACTIVE",
                Facility.status == "ACTIVE",
            )
            .limit(1)
        )
        if db.scalar(stmt) is None:
            raise HTTPException(status_code=403, detail="PERMISSION_DENIED")
        return user

    return dependency
