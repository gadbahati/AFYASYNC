from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_db, require_permission
from app.nursing.schemas import NursingHandoverCreate, NursingNoteCreate, NursingObservationCreate
from app.nursing.service import create_handover, create_note, create_observation

router = APIRouter(prefix="/api/v1/nursing", tags=["Nursing"])


def _error(exc: ValueError) -> HTTPException:
    if str(exc) == "PATIENT_NOT_IN_FACILITY":
        return HTTPException(status.HTTP_403_FORBIDDEN, detail="Patient is not actively enrolled at this facility")
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/observations")
def observations(payload: NursingObservationCreate, db: Session = Depends(get_db), user=Depends(require_permission("encounters.create"))):
    try: return create_observation(db, payload, user.facility_id, user.id)
    except ValueError as exc: raise _error(exc)


@router.post("/notes")
def notes(payload: NursingNoteCreate, db: Session = Depends(get_db), user=Depends(require_permission("encounters.create"))):
    try: return create_note(db, payload, user.facility_id, user.id)
    except ValueError as exc: raise _error(exc)


@router.post("/handovers")
def handovers(payload: NursingHandoverCreate, db: Session = Depends(get_db), user=Depends(require_permission("encounters.create"))):
    try: return create_handover(db, payload, user.facility_id, user.id)
    except ValueError as exc: raise _error(exc)
