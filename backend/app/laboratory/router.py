from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, get_token_payload, require_permission
from app.database import get_db
from app.encounters.models import Encounter
from app.laboratory.models import LabTest
from app.laboratory.schemas import LabOrderCreate, LabOrderResponse, LabTestResponse, ResultCreate, ResultResponse, SampleCollect, SampleReceive, SampleResponse
from app.laboratory.service import collect_sample, create_order, enter_result, receive_sample, verify_result
from app.rbac.models import Staff, User

router = APIRouter(prefix="/api/v1/laboratory", tags=["Laboratory"])


def _staff(db: Session, user: User, facility_id: UUID) -> Staff:
    staff = db.scalar(
        select(Staff).where(
            Staff.person_id == user.person_id,
            Staff.facility_id == facility_id,
            Staff.status == "ACTIVE",
        ).limit(1)
    )
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


@router.get("/tests", response_model=list[LabTestResponse])
def list_tests(
    user: User = Depends(require_permission("lab.order.create")),
    db: Session = Depends(get_db),
):
    """Return the active laboratory test catalogue, including description, specimen and unit price."""
    return list(db.scalars(select(LabTest).where(LabTest.status == "ACTIVE").order_by(LabTest.category, LabTest.name)).all())


@router.post("/orders", response_model=LabOrderResponse, status_code=status.HTTP_201_CREATED)
def order_labs(
    payload: LabOrderCreate,
    user: User = Depends(require_permission("lab.order.create")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _encounter_facility(db, payload.encounter_id, facility_id)
    try:
        return create_order(db, _staff(db, user, facility_id).id, payload.model_dump(), actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/samples/collect", response_model=SampleResponse, status_code=status.HTTP_201_CREATED)
def collect(
    payload: SampleCollect,
    user: User = Depends(require_permission("lab.sample.collect")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    try:
        return collect_sample(db, _staff(db, user, facility_id).id, payload.lab_order_item_id, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/samples/receive", response_model=SampleResponse)
def receive(
    payload: SampleReceive,
    user: User = Depends(require_permission("lab.sample.receive")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    try:
        return receive_sample(db, _staff(db, user, facility_id).id, payload.sample_id, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/results", response_model=ResultResponse, status_code=status.HTTP_201_CREATED)
def result(
    payload: ResultCreate,
    user: User = Depends(require_permission("lab.result.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    try:
        return enter_result(db, _staff(db, user, facility_id).id, payload.model_dump(), actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/results/{result_id}/verify", response_model=ResultResponse)
def verify(
    result_id: UUID,
    user: User = Depends(require_permission("lab.result.verify")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    try:
        return verify_result(db, _staff(db, user, facility_id).id, result_id, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc
