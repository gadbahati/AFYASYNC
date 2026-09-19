"""Patient appointment booking and messaging APIs; facility response APIs."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_facility_context, require_patient_identity
from app.database import get_db
from app.portal.messaging_service import (
    cancel_patient_request,
    create_appointment_request,
    list_bookable_facilities,
    list_facility_departments,
    list_facility_inbox,
    list_facility_requests,
    list_patient_requests,
    list_patient_threads,
    list_thread,
    respond_to_request,
    send_message,
)
from app.portal.service import PortalError, require_patient_person_id
from app.rbac.models import User

patient_router = APIRouter(prefix="/api/v1/portal", tags=["Patient Portal Booking"])
facility_router = APIRouter(prefix="/api/v1/facility", tags=["Facility Appointment Requests"])


class BookRequestIn(BaseModel):
    facility_id: UUID
    reason: str = Field(min_length=5, max_length=2000)
    preferred_date: datetime | None = None
    department_id: UUID | None = None
    patient_notes: str | None = Field(default=None, max_length=2000)


class FacilityRespondIn(BaseModel):
    decision: str = Field(pattern="^(ACCEPTED|DECLINED|RESCHEDULED)$")
    offered_appointment_at: datetime | None = None
    response_notes: str | None = Field(default=None, max_length=2000)
    department_id: UUID | None = None


class MessageIn(BaseModel):
    facility_id: UUID
    body: str = Field(min_length=1, max_length=5000)
    related_request_id: UUID | None = None


class FacilityMessageIn(BaseModel):
    patient_id: UUID
    body: str = Field(min_length=1, max_length=5000)
    related_request_id: UUID | None = None


def _person(user: User) -> UUID:
    try:
        return require_patient_person_id(user.person_id)
    except PortalError as err:
        raise HTTPException(status_code=403, detail=str(err)) from err


@patient_router.get("/facilities")
def portal_list_facilities(
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    _person(user)
    rows = list_bookable_facilities(db)
    return [
        {
            "id": str(f.id),
            "name": f.name,
            "facility_type": f.facility_type,
            "county": f.county,
            "phone": f.phone,
        }
        for f in rows
    ]


@patient_router.get("/facilities/{facility_id}/departments")
def portal_list_departments(
    facility_id: UUID,
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    _person(user)
    rows = list_facility_departments(db, facility_id)
    return [{"id": str(d.id), "name": d.name, "code": d.code} for d in rows]


@patient_router.post("/appointment-requests", status_code=status.HTTP_201_CREATED)
def portal_book(
    payload: BookRequestIn,
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    person_id = _person(user)
    try:
        req = create_appointment_request(
            db,
            patient_id=person_id,
            facility_id=payload.facility_id,
            reason=payload.reason,
            preferred_date=payload.preferred_date,
            department_id=payload.department_id,
            patient_notes=payload.patient_notes,
            actor_user_id=user.id,
        )
        db.commit()
        db.refresh(req)
        return {
            "id": str(req.id),
            "status": req.status,
            "facility_id": str(req.facility_id),
            "reason": req.reason,
            "preferred_date": req.preferred_date,
            "created_at": req.created_at,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@patient_router.get("/appointment-requests")
def portal_my_requests(
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    person_id = _person(user)
    rows = list_patient_requests(db, person_id)
    return [
        {
            "id": str(r.id),
            "facility_id": str(r.facility_id),
            "status": r.status,
            "reason": r.reason,
            "preferred_date": r.preferred_date,
            "offered_appointment_at": r.offered_appointment_at,
            "facility_response_notes": r.facility_response_notes,
            "appointment_id": str(r.appointment_id) if r.appointment_id else None,
            "created_at": r.created_at,
            "responded_at": r.responded_at,
        }
        for r in rows
    ]


@patient_router.post("/appointment-requests/{request_id}/cancel")
def portal_cancel_request(
    request_id: UUID,
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    person_id = _person(user)
    try:
        req = cancel_patient_request(
            db, request_id=request_id, patient_id=person_id, actor_user_id=user.id
        )
        db.commit()
        return {"id": str(req.id), "status": req.status}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@patient_router.get("/messages/threads")
def portal_message_threads(
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    person_id = _person(user)
    return list_patient_threads(db, person_id)


@patient_router.get("/messages/{facility_id}")
def portal_message_thread(
    facility_id: UUID,
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    person_id = _person(user)
    rows = list_thread(db, patient_id=person_id, facility_id=facility_id)
    return [
        {
            "id": str(m.id),
            "sender_type": m.sender_type,
            "body": m.body,
            "created_at": m.created_at,
            "read_at": m.read_at,
        }
        for m in rows
    ]


@patient_router.post("/messages", status_code=status.HTTP_201_CREATED)
def portal_send_message(
    payload: MessageIn,
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    person_id = _person(user)
    try:
        msg = send_message(
            db,
            patient_id=person_id,
            facility_id=payload.facility_id,
            body=payload.body,
            sender_type="PATIENT",
            sender_user_id=user.id,
            related_request_id=payload.related_request_id,
        )
        db.commit()
        db.refresh(msg)
        return {"id": str(msg.id), "created_at": msg.created_at}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@facility_router.get("/appointment-requests")
def facility_list_requests(
    status_filter: str | None = Query(default=None, alias="status"),
    user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
    db: Session = Depends(get_db),
):
    rows = list_facility_requests(db, facility_id, status=status_filter)
    return [
        {
            "id": str(r.id),
            "patient_id": str(r.patient_id),
            "status": r.status,
            "reason": r.reason,
            "preferred_date": r.preferred_date,
            "patient_notes": r.patient_notes,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@facility_router.post("/appointment-requests/{request_id}/respond")
def facility_respond(
    request_id: UUID,
    payload: FacilityRespondIn,
    user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
    db: Session = Depends(get_db),
):
    try:
        req = respond_to_request(
            db,
            request_id=request_id,
            facility_id=facility_id,
            decision=payload.decision,
            offered_appointment_at=payload.offered_appointment_at,
            response_notes=payload.response_notes,
            department_id=payload.department_id,
            actor_user_id=user.id,
        )
        db.commit()
        db.refresh(req)
        return {
            "id": str(req.id),
            "status": req.status,
            "offered_appointment_at": req.offered_appointment_at,
            "appointment_id": str(req.appointment_id) if req.appointment_id else None,
        }
    except ValueError as exc:
        code = str(exc)
        status_code = 404 if code == "REQUEST_NOT_FOUND" else 400
        raise HTTPException(status_code=status_code, detail=code) from exc


@facility_router.get("/messages/inbox")
def facility_inbox(
    user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
    db: Session = Depends(get_db),
):
    return list_facility_inbox(db, facility_id)


@facility_router.get("/messages/{patient_id}")
def facility_thread(
    patient_id: UUID,
    user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
    db: Session = Depends(get_db),
):
    rows = list_thread(db, patient_id=patient_id, facility_id=facility_id)
    return [
        {
            "id": str(m.id),
            "sender_type": m.sender_type,
            "body": m.body,
            "created_at": m.created_at,
            "read_at": m.read_at,
        }
        for m in rows
    ]


@facility_router.post("/messages", status_code=status.HTTP_201_CREATED)
def facility_send_message(
    payload: FacilityMessageIn,
    user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
    db: Session = Depends(get_db),
):
    try:
        msg = send_message(
            db,
            patient_id=payload.patient_id,
            facility_id=facility_id,
            body=payload.body,
            sender_type="FACILITY",
            sender_user_id=user.id,
            related_request_id=payload.related_request_id,
        )
        db.commit()
        return {"id": str(msg.id), "created_at": msg.created_at}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
