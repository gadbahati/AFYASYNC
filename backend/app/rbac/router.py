from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.rbac.schemas import (
    PermissionCreate,
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    StaffCreate,
    StaffListResponse,
    StaffResponse,
    StaffRoleAssign,
    StaffRoleResponse,
    StaffStatusUpdate,
)
from app.rbac.service import (
    assign_staff_role,
    create_permission,
    create_role,
    create_staff,
    list_staff,
    list_staff_roles,
    remove_staff_role,
    update_staff_status,
)

router = APIRouter(prefix="/api/v1", tags=["RBAC"])


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def register_role(
    payload: RoleCreate,
    _: User = Depends(require_permission("rbac.roles.write")),
    db: Session = Depends(get_db),
) -> RoleResponse:
    return create_role(db, payload.model_dump())


@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
def register_permission(
    payload: PermissionCreate,
    _: User = Depends(require_permission("rbac.permissions.write")),
    db: Session = Depends(get_db),
) -> PermissionResponse:
    return create_permission(db, payload.model_dump())


@router.post("/staff", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
def register_staff(
    payload: StaffCreate,
    user: User = Depends(require_permission("staff.create")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> StaffResponse:
    data = payload.model_dump()
    data["facility_id"] = facility_id  # always from token, never from client body
    try:
        return create_staff(db, data, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        mapping = {
            "FACILITY_NOT_FOUND": (status.HTTP_404_NOT_FOUND, "FACILITY_NOT_FOUND"),
            "PERSON_NOT_FOUND": (status.HTTP_404_NOT_FOUND, "PERSON_NOT_FOUND"),
            "INVALID_DEPARTMENT": (status.HTTP_400_BAD_REQUEST, "INVALID_DEPARTMENT"),
            "STAFF_ALREADY_EXISTS": (status.HTTP_409_CONFLICT, "STAFF_ALREADY_EXISTS"),
            "DUPLICATE_EMPLOYEE_NUMBER": (status.HTTP_409_CONFLICT, "DUPLICATE_EMPLOYEE_NUMBER"),
            "FACILITY_CONTEXT_REQUIRED": (status.HTTP_403_FORBIDDEN, "FACILITY_CONTEXT_REQUIRED"),
        }
        http_status, detail = mapping.get(code, (status.HTTP_400_BAD_REQUEST, code))
        raise HTTPException(status_code=http_status, detail=detail) from exc


@router.get("/staff", response_model=StaffListResponse)
def get_staff_list(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: Literal["ACTIVE", "INACTIVE"] | None = Query(default="ACTIVE", alias="status"),
    user: User = Depends(require_permission("staff.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> StaffListResponse:
    try:
        items, total = list_staff(db, facility_id, limit=limit, offset=offset, status=status_filter)
    except ValueError as exc:
        if str(exc) == "INVALID_STAFF_STATUS":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_STAFF_STATUS") from exc
        raise
    return StaffListResponse(items=items, total=total, limit=limit, offset=offset)


@router.patch("/staff/{staff_id}/status", response_model=StaffResponse)
def change_staff_status(
    staff_id: UUID,
    payload: StaffStatusUpdate,
    user: User = Depends(require_permission("staff.manage")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> StaffResponse:
    try:
        return update_staff_status(db, staff_id, facility_id, payload.status, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        mapping = {
            "STAFF_NOT_FOUND": (status.HTTP_404_NOT_FOUND, "STAFF_NOT_FOUND"),
            "INVALID_STAFF_STATUS": (status.HTTP_400_BAD_REQUEST, "INVALID_STAFF_STATUS"),
            "STAFF_STATUS_UNCHANGED": (status.HTTP_400_BAD_REQUEST, "STAFF_STATUS_UNCHANGED"),
            "FACILITY_CONTEXT_REQUIRED": (status.HTTP_403_FORBIDDEN, "FACILITY_CONTEXT_REQUIRED"),
        }
        http_status, detail = mapping.get(code, (status.HTTP_400_BAD_REQUEST, code))
        raise HTTPException(status_code=http_status, detail=detail) from exc


@router.post("/staff/{staff_id}/roles", response_model=StaffRoleResponse, status_code=status.HTTP_201_CREATED)
def assign_role_to_staff(
    staff_id: UUID,
    payload: StaffRoleAssign,
    user: User = Depends(require_permission("staff.roles.assign")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> StaffRoleResponse:
    try:
        return assign_staff_role(db, staff_id, payload.role_id, facility_id, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        mapping = {
            "STAFF_NOT_FOUND": (status.HTTP_404_NOT_FOUND, "STAFF_NOT_FOUND"),
            "STAFF_NOT_ACTIVE": (status.HTTP_400_BAD_REQUEST, "STAFF_NOT_ACTIVE"),
            "ROLE_NOT_FOUND": (status.HTTP_404_NOT_FOUND, "ROLE_NOT_FOUND"),
            "ROLE_ALREADY_ASSIGNED": (status.HTTP_409_CONFLICT, "ROLE_ALREADY_ASSIGNED"),
            "FACILITY_CONTEXT_REQUIRED": (status.HTTP_403_FORBIDDEN, "FACILITY_CONTEXT_REQUIRED"),
        }
        http_status, detail = mapping.get(code, (status.HTTP_400_BAD_REQUEST, code))
        raise HTTPException(status_code=http_status, detail=detail) from exc


@router.delete("/staff/{staff_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_role_from_staff(
    staff_id: UUID,
    role_id: UUID,
    user: User = Depends(require_permission("staff.roles.assign")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> None:
    try:
        remove_staff_role(db, staff_id, role_id, facility_id, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        mapping = {
            "STAFF_NOT_FOUND": (status.HTTP_404_NOT_FOUND, "STAFF_NOT_FOUND"),
            "ROLE_NOT_ASSIGNED": (status.HTTP_404_NOT_FOUND, "ROLE_NOT_ASSIGNED"),
            "FACILITY_CONTEXT_REQUIRED": (status.HTTP_403_FORBIDDEN, "FACILITY_CONTEXT_REQUIRED"),
        }
        http_status, detail = mapping.get(code, (status.HTTP_400_BAD_REQUEST, code))
        raise HTTPException(status_code=http_status, detail=detail) from exc


@router.get("/staff/{staff_id}/roles", response_model=list[StaffRoleResponse])
def get_staff_roles(
    staff_id: UUID,
    user: User = Depends(require_permission("staff.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> list[StaffRoleResponse]:
    try:
        return list_staff_roles(db, staff_id, facility_id)
    except ValueError as exc:
        if str(exc) == "STAFF_NOT_FOUND":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="STAFF_NOT_FOUND") from exc
        raise
