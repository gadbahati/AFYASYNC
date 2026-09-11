from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_token_payload
from app.database import get_db
from app.encounters.models import Encounter
from app.laboratory.schemas import LabOrderCreate, LabOrderResponse, ResultCreate, ResultResponse, SampleCollect, SampleReceive, SampleResponse
from app.laboratory.service import collect_sample, create_order, enter_result, receive_sample, verify_result
from app.rbac.models import Staff, User

router = APIRouter(prefix="/api/v1/laboratory", tags=["Laboratory"])


def _facility(token: dict) -> UUID:
    raw = token.get("facility_id")
    if not raw:
        raise HTTPException(status_code=403, detail="FACILITY_CONTEXT_REQUIRED")
    try:
        return UUID(raw)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=403, detail="INVALID_FACILITY_CONTEXT") from exc


def _staff(db: Session, user: User, facility_id: UUID) -> Staff:
    staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == facility_id, Staff.status == "ACTIVE").limit(1))
    if not staff:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return staff


def _encounter_facility(db: Session, encounter_id: UUID, facility_id: UUID) -> None:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")


def _error(exc: ValueError) -> HTTPException:
    code = str(exc)
    status_code = 404 if code.endswith("NOT_FOUND") else 409 if "STATE" in code or "ALREADY" in code else 400
    return HTTPException(status_code=status_code, detail=code)


@router.post("/orders", response_model=LabOrderResponse, status_code=status.HTTP_201_CREATED)
def order_labs(payload: LabOrderCreate, user: User = Depends(get_current_user), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    facility_id = _facility(token)
    _encounter_facility(db, payload.encounter_id, facility_id)
    try:
        return create_order(db, _staff(db, user, facility_id).id, payload.model_dump(), actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/samples/collect", response_model=SampleResponse, status_code=status.HTTP_201_CREATED)
def collect(payload: SampleCollect, user: User = Depends(get_current_user), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    try:
        return collect_sample(db, _staff(db, user, _facility(token)).id, payload.lab_order_item_id, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/samples/receive", response_model=SampleResponse)
def receive(payload: SampleReceive, user: User = Depends(get_current_user), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    try:
        return receive_sample(db, _staff(db, user, _facility(token)).id, payload.sample_id, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/results", response_model=ResultResponse, status_code=status.HTTP_201_CREATED)
def result(payload: ResultCreate, user: User = Depends(get_current_user), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    try:
        return enter_result(db, _staff(db, user, _facility(token)).id, payload.model_dump(), actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/results/{result_id}/verify", response_model=ResultResponse)
def verify(result_id: UUID, user: User = Depends(get_current_user), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    try:
        return verify_result(db, _staff(db, user, _facility(token)).id, result_id, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc
