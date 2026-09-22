"""Public health surveillance APIs."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.surveillance.service import (
    SurveillanceError,
    aggregate,
    list_facility,
    report_event,
    update_status,
)

router = APIRouter(prefix="/api/v1/surveillance", tags=["Surveillance"])


def _map(err: SurveillanceError) -> HTTPException:
    code = str(err)
    return HTTPException(status_code=404 if "NOT_FOUND" in code else 400, detail=code)


class ReportBody(BaseModel):
    condition_code: str = Field(min_length=2, max_length=40)
    classification: str = Field(default="SUSPECTED", max_length=30)
    person_id: UUID | None = None
    onset_date: date | None = None
    notification_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    staff_id: UUID | None = None


class StatusBody(BaseModel):
    status: str
    classification: str | None = None
    notes: str | None = Field(default=None, max_length=2000)


@router.post("/events")
def create_event(
    body: ReportBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        event = report_event(
            db,
            facility_id=facility_id,
            condition_code=body.condition_code,
            classification=body.classification,
            person_id=body.person_id,
            onset_date=body.onset_date,
            notification_date=body.notification_date,
            notes=body.notes,
            staff_id=body.staff_id,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(event.id), "status": event.status, "condition_code": event.condition_code}
    except SurveillanceError as e:
        raise _map(e) from e


@router.get("/events")
def list_events(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    status: str | None = Query(default=None, max_length=30),
    condition_code: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=50, ge=1, le=200),
):
    _ = user
    return {
        "events": list_facility(
            db,
            facility_id=facility_id,
            status=status,
            condition_code=condition_code,
            limit=limit,
        )
    }


@router.post("/events/{event_id}/status")
def set_status(
    event_id: UUID,
    body: StatusBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        event = update_status(
            db,
            facility_id=facility_id,
            event_id=event_id,
            status=body.status,
            classification=body.classification,
            notes=body.notes,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(event.id), "status": event.status, "classification": event.classification}
    except SurveillanceError as e:
        raise _map(e) from e


@router.get("/aggregates")
def get_aggregates(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=30, ge=1, le=365),
    county: str | None = Query(default=None, max_length=80),
):
    _ = user
    return aggregate(db, days=days, county=county)
