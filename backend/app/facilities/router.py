from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_facility_context, require_permission
from app.database import get_db
from app.facilities.schemas import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentStatusUpdate,
    FacilityCreate,
    FacilityResponse,
    FacilityStatusUpdate,
    FacilityUpdate,
)
from app.facilities.service import (
    create_department,
    create_facility,
    get_facility,
    list_departments,
    list_facilities,
    update_department_status,
    update_facility,
    update_facility_status,
)
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/facilities", tags=["Facilities"])


@router.post("", response_model=FacilityResponse, status_code=status.HTTP_201_CREATED)
def register_facility(
    payload: FacilityCreate,
    user: User = Depends(require_permission("facilities.create")),
    db: Session = Depends(get_db),
) -> FacilityResponse:
    return create_facility(db, payload.model_dump(), actor_user_id=user.id)


@router.get("", response_model=list[FacilityResponse])
def get_facilities(
    limit: int = Query(default=50, ge=1, le=100),
    _: User = Depends(require_permission("facilities.read")),
    db: Session = Depends(get_db),
) -> list[FacilityResponse]:
    return list_facilities(db, limit)


@router.get("/me", response_model=FacilityResponse)
def get_current_facility(
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("facilities.read")),
    db: Session = Depends(get_db),
) -> FacilityResponse:
    facility = get_facility(db, facility_id)
    if facility is None:
        raise HTTPException(status_code=404, detail="FACILITY_NOT_FOUND")
    return facility


@router.patch("/me", response_model=FacilityResponse)
def update_current_facility(
    payload: FacilityUpdate,
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("facilities.manage")),
    db: Session = Depends(get_db),
) -> FacilityResponse:
    try:
        return update_facility(
            db,
            facility_id,
            payload.model_dump(exclude_unset=True),
            actor_user_id=user.id,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "FACILITY_NOT_FOUND":
            raise HTTPException(status_code=404, detail=code) from exc
        if code == "NO_CHANGES":
            raise HTTPException(status_code=400, detail=code) from exc
        raise


@router.patch("/me/status", response_model=FacilityResponse)
def change_current_facility_status(
    payload: FacilityStatusUpdate,
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("facilities.manage")),
    db: Session = Depends(get_db),
) -> FacilityResponse:
    try:
        return update_facility_status(db, facility_id, payload.status, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        mapping = {
            "FACILITY_NOT_FOUND": 404,
            "INVALID_FACILITY_STATUS": 400,
            "FACILITY_STATUS_UNCHANGED": 400,
        }
        raise HTTPException(status_code=mapping.get(code, 400), detail=code) from exc


@router.post(
    "/{facility_id}/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_department(
    facility_id: UUID,
    payload: DepartmentCreate,
    user: User = Depends(require_permission("facilities.department.write")),
    context_facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> DepartmentResponse:
    if facility_id != context_facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try:
        return create_department(
            db,
            facility_id,
            payload.model_dump(),
            actor_user_id=user.id,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "FACILITY_NOT_FOUND":
            raise HTTPException(status_code=404, detail=code) from exc
        if code == "DEPARTMENT_CODE_EXISTS":
            raise HTTPException(status_code=409, detail=code) from exc
        raise


@router.get("/{facility_id}/departments", response_model=list[DepartmentResponse])
def get_departments(
    facility_id: UUID,
    _: User = Depends(require_permission("facilities.department.read")),
    context_facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> list[DepartmentResponse]:
    if facility_id != context_facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return list_departments(db, facility_id)


@router.patch("/{facility_id}/departments/{department_id}/status", response_model=DepartmentResponse)
def change_department_status(
    facility_id: UUID,
    department_id: UUID,
    payload: DepartmentStatusUpdate,
    user: User = Depends(require_permission("facilities.department.write")),
    context_facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> DepartmentResponse:
    if facility_id != context_facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try:
        return update_department_status(
            db,
            facility_id,
            department_id,
            payload.status,
            actor_user_id=user.id,
        )
    except ValueError as exc:
        code = str(exc)
        mapping = {
            "DEPARTMENT_NOT_FOUND": 404,
            "INVALID_DEPARTMENT_STATUS": 400,
            "DEPARTMENT_STATUS_UNCHANGED": 400,
        }
        raise HTTPException(status_code=mapping.get(code, 400), detail=code) from exc
