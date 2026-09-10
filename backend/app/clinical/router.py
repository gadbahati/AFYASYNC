from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.clinical.schemas import (
    ConsultationCreate,
    ConsultationResponse,
    DiagnosisCreate,
    DiagnosisResponse,
    VitalCreate,
    VitalResponse,
)
from app.clinical.service import add_diagnosis, create_or_update_consultation, record_vitals
from app.database import get_db
from app.rbac.models import Staff, User

router = APIRouter(prefix="/api/v1/encounters", tags=["Clinical"])


def _staff_for_user(db: Session, user: User, encounter_facility_id: UUID) -> Staff:
    staff = db.scalar(
        __import__("sqlalchemy").select(Staff).where(
            Staff.person_id == user.person_id,
            Staff.facility_id == encounter_facility_id,
            Staff.status == "ACTIVE",
        ).limit(1)
    )
    if staff is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return staff


@router.post("/{encounter_id}/vitals", response_model=VitalResponse, status_code=status.HTTP_201_CREATED)
def create_vitals(
    encounter_id: UUID,
    payload: VitalCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VitalResponse:
    from app.encounters.models import Encounter
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
    staff = _staff_for_user(db, user, encounter.facility_id)
    try:
        return record_vitals(db, encounter_id, staff.id, payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{encounter_id}/consultation", response_model=ConsultationResponse)
def save_consultation(
    encounter_id: UUID,
    payload: ConsultationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsultationResponse:
    from app.encounters.models import Encounter
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
    staff = _staff_for_user(db, user, encounter.facility_id)
    try:
        return create_or_update_consultation(db, encounter_id, staff.id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{encounter_id}/diagnoses", response_model=DiagnosisResponse, status_code=status.HTTP_201_CREATED)
def create_diagnosis(
    encounter_id: UUID,
    payload: DiagnosisCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiagnosisResponse:
    from app.encounters.models import Encounter
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
    staff = _staff_for_user(db, user, encounter.facility_id)
    try:
        return add_diagnosis(db, encounter_id, staff.id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
