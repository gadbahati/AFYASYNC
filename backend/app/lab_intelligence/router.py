"""Laboratory Intelligence APIs."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.facilities.models import Staff
from app.lab_intelligence.models import LabCriticalAlert, LabTestReference
from app.lab_intelligence.service import (
    acknowledge_critical,
    list_open_criticals,
    tat_summary,
    upsert_test_reference,
)
from app.rbac.models import User
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/lab-intelligence", tags=["Lab Intelligence"])

LAB_READ = "lab.order.create"  # reuse existing lab permission
LAB_WRITE = "lab.result.enter"


def _staff(db: Session, user: User, facility_id: UUID) -> Staff:
    staff = db.scalar(
        select(Staff).where(
            Staff.user_id == user.id,
            Staff.facility_id == facility_id,
            Staff.status == "ACTIVE",
        )
    )
    if staff is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return staff


class ReferenceUpsert(BaseModel):
    test_id: UUID
    unit: str | None = None
    ref_low: Decimal | None = None
    ref_high: Decimal | None = None
    critical_low: Decimal | None = None
    critical_high: Decimal | None = None
    tat_target_minutes: int | None = Field(default=None, ge=1, le=10080)
    sex_specific: str | None = Field(default=None, max_length=10)
    notes: str | None = Field(default=None, max_length=2000)


class AckBody(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


@router.put("/references")
def put_reference(
    payload: ReferenceUpsert,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(LAB_READ)),
):
    _ = facility_id
    try:
        row = upsert_test_reference(db, test_id=payload.test_id, data=payload.model_dump())
        db.commit()
        return {
            "test_id": str(row.test_id),
            "ref_low": str(row.ref_low) if row.ref_low is not None else None,
            "ref_high": str(row.ref_high) if row.ref_high is not None else None,
            "critical_low": str(row.critical_low) if row.critical_low is not None else None,
            "critical_high": str(row.critical_high) if row.critical_high is not None else None,
            "status": row.status,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/critical")
def open_criticals(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(LAB_READ)),
):
    rows = list_open_criticals(db, facility_id, limit=limit)
    return [
        {
            "id": str(r.id),
            "patient_id": str(r.patient_id),
            "encounter_id": str(r.encounter_id),
            "test_code": r.test_code,
            "test_name": r.test_name,
            "result_value": r.result_value,
            "unit": r.unit,
            "flag": r.flag,
            "severity": r.severity,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/critical/{alert_id}/acknowledge")
def ack_critical(
    alert_id: UUID,
    body: AckBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(LAB_WRITE)),
):
    staff = _staff(db, user, facility_id)
    try:
        alert = acknowledge_critical(
            db,
            alert_id=alert_id,
            facility_id=facility_id,
            staff_id=staff.id,
            note=body.note,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(alert.id), "status": alert.status}
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=404 if "NOT_FOUND" in code else 400,
            detail=code,
        ) from exc


@router.get("/tat")
def get_tat(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(LAB_READ)),
):
    return tat_summary(db, facility_id, days=days)
