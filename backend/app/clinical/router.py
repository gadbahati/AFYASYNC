from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_token_payload, require_permission
from app.clinical.schemas import ConsultationCreate, ConsultationResponse, DiagnosisCreate, DiagnosisResponse, VitalCreate, VitalResponse
from app.clinical.service import add_diagnosis, create_or_update_consultation, record_vitals
from app.database import get_db
from app.encounters.models import Encounter
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/encounters", tags=["Clinical"])


def _context(token: dict) -> UUID:
    raw = token.get("facility_id")
    if not raw:
        raise HTTPException(status_code=403, detail="FACILITY_CONTEXT_REQUIRED")
    try:
        return UUID(raw)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=403, detail="INVALID_FACILITY_CONTEXT") from exc


def _encounter(db: Session, encounter_id: UUID, facility_id: UUID) -> Encounter:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return encounter


@router.post("/{encounter_id}/vitals", response_model=VitalResponse, status_code=status.HTTP_201_CREATED)
def create_vitals(encounter_id: UUID, payload: VitalCreate, user: User = Depends(require_permission("clinical.vitals.write")), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> VitalResponse:
    facility_id = _context(token)
    encounter = _encounter(db, encounter_id, facility_id)
    try:
        from app.rbac.models import Staff
        staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == facility_id, Staff.status == "ACTIVE").limit(1))
        if staff is None:
            raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
        return record_vitals(db, encounter.id, staff.id, payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{encounter_id}/consultation", response_model=ConsultationResponse)
def save_consultation(encounter_id: UUID, payload: ConsultationCreate, user: User = Depends(require_permission("clinical.consultation.write")), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> ConsultationResponse:
    facility_id = _context(token)
    encounter = _encounter(db, encounter_id, facility_id)
    try:
        from app.rbac.models import Staff
        staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == facility_id, Staff.status == "ACTIVE").limit(1))
        if staff is None:
            raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
        return create_or_update_consultation(db, encounter.id, staff.id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{encounter_id}/diagnoses", response_model=DiagnosisResponse, status_code=status.HTTP_201_CREATED)
def create_diagnosis(encounter_id: UUID, payload: DiagnosisCreate, user: User = Depends(require_permission("clinical.diagnosis.write")), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> DiagnosisResponse:
    facility_id = _context(token)
    encounter = _encounter(db, encounter_id, facility_id)
    try:
        from app.rbac.models import Staff
        staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == facility_id, Staff.status == "ACTIVE").limit(1))
        if staff is None:
            raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
        return add_diagnosis(db, encounter.id, staff.id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
