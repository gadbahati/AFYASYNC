"""Ambulance / emergency transport APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ambulance.service import (
    AmbulanceError,
    board_summary,
    create_request,
    list_facility,
    list_patient,
    update_status,
)
from app.auth.dependencies import get_facility_context, require_patient_identity, require_permission
from app.database import get_db
from app.portal.service import PortalError, require_patient_person_id
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/ambulance", tags=["Ambulance"])


def _map(err: AmbulanceError) -> HTTPException:
    code = str(err)
    sc = 404 if "NOT_FOUND" in code else 400
    return HTTPException(status_code=sc, detail=code)


def _person(user: User) -> UUID:
    try:
        return require_patient_person_id(user.person_id)
    except PortalError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


class CreateBody(BaseModel):
    facility_id: UUID
    requester_phone: str = Field(min_length=7, max_length=30)
    pickup_location: str = Field(min_length=3, max_length=300)
    destination: str | None = Field(default=None, max_length=300)
    clinical_note: str | None = Field(default=None, max_length=500)
    priority: str = Field(default="URGENT", max_length=20)


class FacilityCreateBody(BaseModel):
    requester_phone: str = Field(min_length=7, max_length=30)
    pickup_location: str = Field(min_length=3, max_length=300)
    destination: str | None = Field(default=None, max_length=300)
    clinical_note: str | None = Field(default=None, max_length=500)
    priority: str = Field(default="URGENT", max_length=20)
    person_id: UUID | None = None


class StatusBody(BaseModel):
    status: str
    vehicle_ref: str | None = Field(default=None, max_length=80)
    eta_minutes: float | None = None
    dispatcher_message: str | None = Field(default=None, max_length=500)
    outcome_note: str | None = Field(default=None, max_length=4000)
    staff_id: UUID | None = None


@router.post("/requests")
def patient_create(
    body: CreateBody,
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    person_id = _person(user)
    try:
        req = create_request(
            db,
            facility_id=body.facility_id,
            requester_phone=body.requester_phone,
            pickup_location=body.pickup_location,
            destination=body.destination,
            clinical_note=body.clinical_note,
            priority=body.priority,
            person_id=person_id,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(req.id), "status": req.status}
    except AmbulanceError as e:
        raise _map(e) from e


@router.get("/my-requests")
def my_requests(
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
    limit: int = Query(default=30, ge=1, le=100),
):
    return {"requests": list_patient(db, person_id=_person(user), limit=limit)}


@router.post("/facility/requests")
def facility_create(
    body: FacilityCreateBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        req = create_request(
            db,
            facility_id=facility_id,
            requester_phone=body.requester_phone,
            pickup_location=body.pickup_location,
            destination=body.destination,
            clinical_note=body.clinical_note,
            priority=body.priority,
            person_id=body.person_id,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(req.id), "status": req.status}
    except AmbulanceError as e:
        raise _map(e) from e


@router.get("/facility/board")
def facility_board(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    status_filter: str | None = Query(default=None, alias="status", max_length=30),
    limit: int = Query(default=50, ge=1, le=100),
):
    _ = user
    return {
        "summary": board_summary(db, facility_id=facility_id),
        "requests": list_facility(db, facility_id=facility_id, status=status_filter, limit=limit),
    }


@router.post("/facility/requests/{request_id}/status")
def set_status(
    request_id: UUID,
    body: StatusBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        req = update_status(
            db,
            facility_id=facility_id,
            request_id=request_id,
            new_status=body.status,
            vehicle_ref=body.vehicle_ref,
            eta_minutes=body.eta_minutes,
            dispatcher_message=body.dispatcher_message,
            outcome_note=body.outcome_note,
            staff_id=body.staff_id,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(req.id), "status": req.status, "vehicle_ref": req.vehicle_ref, "eta_minutes": req.eta_minutes}
    except AmbulanceError as e:
        raise _map(e) from e
