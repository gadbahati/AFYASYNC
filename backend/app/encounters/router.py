from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.context.service import resolve_facility_ids
from app.audit.service import record_audit
from app.database import get_db
from app.encounters.schemas import EncounterCreate, EncounterListResponse, EncounterResponse
from app.encounters.service import close_encounter, create_encounter, get_encounter_for_facility, list_encounters_for_facility
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/encounters", tags=["Encounters"])


def _error(exc: ValueError) -> HTTPException:
    code = str(exc)
    mapping = {
        "PATIENT_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "FACILITY_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "DEPARTMENT_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "PATIENT_NOT_IN_FACILITY": status.HTTP_403_FORBIDDEN,
        "ENCOUNTER_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "FACILITY_ACCESS_DENIED": status.HTTP_403_FORBIDDEN,
        "ENCOUNTER_CLOSED": status.HTTP_409_CONFLICT,
        "INVALID_COVERAGE_MODE": status.HTTP_400_BAD_REQUEST,
        "COVERAGE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "COVERAGE_PATIENT_MISMATCH": status.HTTP_400_BAD_REQUEST,
        "PAYER_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "PROVIDER_STAFF_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "PROVIDER_STAFF_DEPARTMENT_MISMATCH": status.HTTP_400_BAD_REQUEST,
    }
    return HTTPException(status_code=mapping.get(code, status.HTTP_400_BAD_REQUEST), detail=code)


@router.post("", response_model=EncounterResponse, status_code=status.HTTP_201_CREATED)
def create(payload: EncounterCreate, user: User = Depends(require_permission("encounters.create")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["facility_id"] = facility_id
    try:
        return create_encounter(db, data, created_by=user.id, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("", response_model=EncounterListResponse)
def list_all(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    scope: str = Query(default="facility", description="facility | network | county | national"),
    user: User = Depends(require_permission("encounters.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    facility_ids = resolve_facility_ids(db, user=user, token_facility_id=facility_id, scope=scope)
    items, total = list_encounters_for_facility(
        db, facility_id, limit=limit, offset=offset, facility_ids=facility_ids
    )
    return EncounterListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{encounter_id}", response_model=EncounterResponse)
def get(encounter_id: UUID, user: User = Depends(require_permission("encounters.read")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    try:
        encounter = get_encounter_for_facility(db, encounter_id, facility_id)
    except ValueError as exc:
        raise _error(exc) from exc
    record_audit(db, action="VIEW_ENCOUNTER", resource_type="ENCOUNTER", resource_id=str(encounter.id), result="SUCCESS", user_id=user.id, facility_id=facility_id, patient_id=encounter.patient_id, commit=True)
    return encounter


@router.post("/{encounter_id}/close", response_model=EncounterResponse)
def close(encounter_id: UUID, user: User = Depends(require_permission("encounters.close")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    try:
        encounter = get_encounter_for_facility(db, encounter_id, facility_id)
        return close_encounter(db, encounter.id, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc
