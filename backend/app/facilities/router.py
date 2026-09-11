from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.facilities.schemas import (
    DepartmentCreate,
    DepartmentResponse,
    FacilityCreate,
    FacilityResponse,
)
from app.facilities.service import (
    create_department,
    create_facility,
    list_departments,
    list_facilities,
)
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/facilities", tags=["Facilities"])


@router.post("", response_model=FacilityResponse, status_code=status.HTTP_201_CREATED)
def register_facility(payload: FacilityCreate, db: Session = Depends(get_db)) -> FacilityResponse:
    return create_facility(db, payload.model_dump())


@router.get("", response_model=list[FacilityResponse])
def get_facilities(
    limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db)
) -> list[FacilityResponse]:
    return list_facilities(db, limit)


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
        if str(exc) == "FACILITY_NOT_FOUND":
            raise HTTPException(status_code=404, detail="FACILITY_NOT_FOUND") from exc
        raise


@router.get("/{facility_id}/departments", response_model=list[DepartmentResponse])
def get_departments(
    facility_id: UUID,
    context_facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> list[DepartmentResponse]:
    if facility_id != context_facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return list_departments(db, facility_id)
