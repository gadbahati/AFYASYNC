from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_token_payload
from app.database import get_db
from app.encounters.schemas import EncounterCreate, EncounterResponse
from app.encounters.service import close_encounter, create_encounter, get_encounter
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/encounters", tags=["Encounters"])


def _facility(payload: dict) -> UUID:
    raw = payload.get("facility_id")
    if not raw:
        raise HTTPException(status_code=403, detail="FACILITY_CONTEXT_REQUIRED")
    try:
        return UUID(raw)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=403, detail="INVALID_FACILITY_CONTEXT") from exc


def _error(exc: ValueError) -> HTTPException:
    code = str(exc)
    mapping = {"PATIENT_NOT_FOUND": 404, "FACILITY_NOT_FOUND": 404, "DEPARTMENT_NOT_FOUND": 404, "ENCOUNTER_NOT_FOUND": 404, "ENCOUNTER_CLOSED": 409}
    return HTTPException(status_code=mapping.get(code, 400), detail=code)


@router.post("", response_model=EncounterResponse, status_code=status.HTTP_201_CREATED)
def create(payload: EncounterCreate, user: User = Depends(get_current_user), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    facility_id = _facility(token)
    if payload.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try:
        return create_encounter(db, payload.model_dump(), user.id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/{encounter_id}", response_model=EncounterResponse)
def get(encounter_id: UUID, _: User = Depends(get_current_user), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    encounter = get_encounter(db, encounter_id)
    if encounter.facility_id != _facility(token):
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return encounter


@router.post("/{encounter_id}/close", response_model=EncounterResponse)
def close(encounter_id: UUID, _: User = Depends(get_current_user), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    encounter = get_encounter(db, encounter_id)
    if encounter.facility_id != _facility(token):
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try:
        return close_encounter(db, encounter_id)
    except ValueError as exc:
        raise _error(exc) from exc
