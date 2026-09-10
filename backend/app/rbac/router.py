from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.rbac.schemas import (
    PermissionCreate,
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    StaffCreate,
    StaffResponse,
)
from app.rbac.service import create_permission, create_role, create_staff, list_staff

router = APIRouter(prefix="/api/v1", tags=["RBAC"])


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def register_role(payload: RoleCreate, db: Session = Depends(get_db)) -> RoleResponse:
    return create_role(db, payload.model_dump())


@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
def register_permission(
    payload: PermissionCreate, db: Session = Depends(get_db)
) -> PermissionResponse:
    return create_permission(db, payload.model_dump())


@router.post("/staff", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
def register_staff(payload: StaffCreate, db: Session = Depends(get_db)) -> StaffResponse:
    try:
        return create_staff(db, payload.model_dump())
    except ValueError as exc:
        code = str(exc)
        messages = {
            "FACILITY_NOT_FOUND": (404, "FACILITY_NOT_FOUND"),
            "PERSON_NOT_FOUND": (404, "PERSON_NOT_FOUND"),
            "INVALID_DEPARTMENT": (400, "INVALID_DEPARTMENT"),
        }
        http_status, detail = messages.get(code, (400, code))
        raise HTTPException(status_code=http_status, detail=detail) from exc


@router.get("/facilities/{facility_id}/staff", response_model=list[StaffResponse])
def get_staff(
    facility_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[StaffResponse]:
    return list_staff(db, facility_id, limit)
