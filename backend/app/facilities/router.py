from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

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
    db: Session = Depends(get_db),
) -> DepartmentResponse:
    try:
        return create_department(db, facility_id, payload.model_dump())
    except ValueError as exc:
        if str(exc) == "FACILITY_NOT_FOUND":
            raise HTTPException(status_code=404, detail="FACILITY_NOT_FOUND") from exc
        raise


@router.get("/{facility_id}/departments", response_model=list[DepartmentResponse])
def get_departments(
    facility_id: UUID, db: Session = Depends(get_db)
) -> list[DepartmentResponse]:
    return list_departments(db, facility_id)
