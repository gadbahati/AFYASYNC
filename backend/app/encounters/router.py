from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.encounters.schemas import EncounterCreate, EncounterResponse
from app.encounters.service import close_encounter, create_encounter, get_encounter_for_facility
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/encounters", tags=["Encounters"])


def _error(exc: ValueError) -> HTTPException:
    code = str(exc)
    mapping = {
        "PATIENT_NOT_FOUND": 404,
        "FACILITY_NOT_FOUND": 404,
        "DEPARTMENT_NOT_FOUND": 404,
        "ENCOUNTER_NOT_FOUND": 404,
        "PATIENT_NOT_IN_FACILITY": 404,
        "FACILITY_ACCESS_DENIED": 403,
        "ENCOUNTER_CLOSED": 409,
    }
    return HTTPException(status_code=mapping.get(code, 400), detail=code)


@router.post("", response_model=EncounterResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: EncounterCreate,
    user: User = Depends(require_permission("encounters.create")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    # Facility always from token — never trust client body for isolation
    data = payload.model_dump()
    data["facility_id"] = facility_id
    try:
        return create_encounter(db, data, user.id, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/{encounter_id}", response_model=EncounterResponse)
def get(
    encounter_id: UUID,
    user: User = Depends(require_permission("encounters.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    try:
        encounter = get_encounter_for_facility(db, encounter_id, facility_id)
    except ValueError as exc:
        raise _error(exc) from exc

    record_audit(
        db,
        action="VIEW_ENCOUNTER",
        resource_type="ENCOUNTER",
        resource_id=str(encounter.id),
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        patient_id=encounter.patient_id,
        commit=True,
    )
    return encounter


@router.post("/{encounter_id}/close", response_model=EncounterResponse)
def close(
    encounter_id: UUID,
    user: User = Depends(require_permission("encounters.close")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    try:
        encounter = get_encounter_for_facility(db, encounter_id, facility_id)
        return close_encounter(db, encounter.id, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc
