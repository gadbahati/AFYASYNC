from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_db, require_permission
from app.emergency.schemas import EmergencyDisposition, EmergencyTriageCreate, EmergencyVisitCreate, EmergencyVisitResponse
from app.emergency.service import create_emergency_visit, record_triage, update_disposition

router = APIRouter(prefix="/api/v1/emergency", tags=["Emergency"])


def _error(exc: ValueError) -> HTTPException:
    mapping = {
        "PATIENT_NOT_IN_FACILITY": (status.HTTP_403_FORBIDDEN, "Patient is not actively enrolled at this facility"),
        "INVALID_TRIAGE_LEVEL": (status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid triage level"),
        "EMERGENCY_VISIT_NOT_FOUND": (status.HTTP_404_NOT_FOUND, "Emergency visit not found"),
        "INVALID_DISPOSITION": (status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid emergency disposition"),
    }
    code, detail = mapping.get(str(exc), (status.HTTP_400_BAD_REQUEST, str(exc)))
    return HTTPException(code, detail=detail)


@router.post("/visits", response_model=EmergencyVisitResponse, status_code=status.HTTP_201_CREATED)
def create_visit(payload: EmergencyVisitCreate, db: Session = Depends(get_db), user=Depends(require_permission("encounters.create"))):
    try:
        return create_emergency_visit(db, payload.patient_id, user.facility_id, user.id, arrival_mode=payload.arrival_mode, chief_complaint=payload.chief_complaint, triage_level=payload.triage_level, notes=payload.notes)
    except ValueError as exc:
        raise _error(exc)


@router.post("/visits/{visit_id}/triage")
def triage(visit_id: UUID, payload: EmergencyTriageCreate, db: Session = Depends(get_db), user=Depends(require_permission("encounters.create"))):
    try:
        return record_triage(db, visit_id, user.facility_id, user.id, **payload.model_dump())
    except ValueError as exc:
        raise _error(exc)


@router.post("/visits/{visit_id}/disposition", response_model=EmergencyVisitResponse)
def disposition(visit_id: UUID, payload: EmergencyDisposition, db: Session = Depends(get_db), user=Depends(require_permission("encounters.create"))):
    try:
        return update_disposition(db, visit_id, user.facility_id, user.id, payload.disposition, payload.notes)
    except ValueError as exc:
        raise _error(exc)
