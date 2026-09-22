"""Telemedicine APIs — patient request + facility coordination."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_patient_identity, require_permission
from app.database import get_db
from app.portal.service import PortalError, require_patient_person_id
from app.rbac.models import User
from app.telemedicine.service import (
    TeleError,
    complete_consult,
    facility_respond,
    list_facility,
    list_patient,
    patient_cancel,
    patient_request,
)

router = APIRouter(prefix="/api/v1/telemedicine", tags=["Telemedicine"])


def _person_id(user: User) -> UUID:
    try:
        return require_patient_person_id(user.person_id)
    except PortalError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err


def _map(err: TeleError) -> HTTPException:
    code = str(err)
    status_code = 404 if "NOT_FOUND" in code else 400
    return HTTPException(status_code=status_code, detail=code)


class PatientRequestBody(BaseModel):
    facility_id: UUID
    reason: str = Field(min_length=5, max_length=500)
    urgency: str = Field(default="ROUTINE", max_length=20)
    preferred_window: str | None = Field(default=None, max_length=120)


class FacilityRespondBody(BaseModel):
    decision: str = Field(description="ACCEPTED or DENIED")
    facility_message: str | None = Field(default=None, max_length=500)
    scheduled_at: datetime | None = None
    staff_id: UUID | None = None


class CompleteBody(BaseModel):
    clinical_summary: str = Field(min_length=3, max_length=4000)


# ---- Patient ----
@router.post("/requests")
def create_request(
    body: PatientRequestBody,
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    person_id = _person_id(user)
    try:
        req = patient_request(
            db,
            person_id=person_id,
            facility_id=body.facility_id,
            reason=body.reason,
            urgency=body.urgency,
            preferred_window=body.preferred_window,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(req.id), "status": req.status}
    except TeleError as exc:
        raise _map(exc) from exc


@router.get("/my-requests")
def my_requests(
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
    limit: int = Query(default=30, ge=1, le=100),
):
    person_id = _person_id(user)
    return {"requests": list_patient(db, person_id=person_id, limit=limit)}


@router.post("/requests/{request_id}/cancel")
def cancel(
    request_id: UUID,
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    person_id = _person_id(user)
    try:
        req = patient_cancel(db, person_id=person_id, request_id=request_id, actor_user_id=user.id)
        db.commit()
        return {"id": str(req.id), "status": req.status}
    except TeleError as exc:
        raise _map(exc) from exc


# ---- Facility ----
@router.get("/facility/inbox")
def facility_inbox(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    status_filter: str | None = Query(default=None, alias="status", max_length=30),
    limit: int = Query(default=50, ge=1, le=100),
):
    _ = user
    return {"requests": list_facility(db, facility_id=facility_id, status=status_filter, limit=limit)}


@router.post("/facility/requests/{request_id}/respond")
def respond(
    request_id: UUID,
    body: FacilityRespondBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        req = facility_respond(
            db,
            facility_id=facility_id,
            request_id=request_id,
            decision=body.decision,
            facility_message=body.facility_message,
            scheduled_at=body.scheduled_at,
            staff_id=body.staff_id,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(req.id), "status": req.status, "scheduled_at": req.scheduled_at.isoformat() if req.scheduled_at else None}
    except TeleError as exc:
        raise _map(exc) from exc


@router.post("/facility/requests/{request_id}/complete")
def complete(
    request_id: UUID,
    body: CompleteBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        req = complete_consult(
            db,
            facility_id=facility_id,
            request_id=request_id,
            clinical_summary=body.clinical_summary,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(req.id), "status": req.status}
    except TeleError as exc:
        raise _map(exc) from exc
