from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.laboratory.schemas import LabOrderCreate, LabOrderResponse, ResultCreate, ResultResponse, SampleCollect, SampleReceive, SampleResponse
from app.laboratory.service import collect_sample, create_order, enter_result, receive_sample, verify_result
from app.rbac.models import Staff, User
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/laboratory", tags=["Laboratory"])


def _staff(db: Session, user: User) -> Staff:
    staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.status == "ACTIVE").limit(1))
    if not staff:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return staff


def _error(exc: ValueError) -> HTTPException:
    code = str(exc)
    status_code = 404 if code.endswith("NOT_FOUND") else 409 if "STATE" in code or "ALREADY" in code else 400
    return HTTPException(status_code=status_code, detail=code)


@router.post("/orders", response_model=LabOrderResponse, status_code=status.HTTP_201_CREATED)
def order_labs(payload: LabOrderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return create_order(db, _staff(db, user).id, payload.model_dump())
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/samples/collect", response_model=SampleResponse, status_code=status.HTTP_201_CREATED)
def collect(payload: SampleCollect, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return collect_sample(db, _staff(db, user).id, payload.lab_order_item_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/samples/receive", response_model=SampleResponse)
def receive(payload: SampleReceive, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return receive_sample(db, _staff(db, user).id, payload.sample_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/results", response_model=ResultResponse, status_code=status.HTTP_201_CREATED)
def result(payload: ResultCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return enter_result(db, _staff(db, user).id, payload.model_dump())
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/results/{result_id}/verify", response_model=ResultResponse)
def verify(result_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return verify_result(db, _staff(db, user).id, result_id)
    except ValueError as exc:
        raise _error(exc) from exc
