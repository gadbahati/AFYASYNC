"""Imaging / Radiology Intelligence APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.facilities.models import Staff
from app.imaging_intelligence.service import (
    acknowledge_finding,
    check_contrast_safety,
    imaging_tat_summary,
    list_open_findings,
    register_critical_finding,
    upsert_test_safety,
)
from app.radiology.models import ImagingOrder, ImagingReport, ImagingTest
from app.rbac.models import User
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/imaging-intelligence", tags=["Imaging Intelligence"])

READ = "patients.record.read"
WRITE = "encounters.create"


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


class ContrastCheckIn(BaseModel):
    patient_id: UUID
    test_id: UUID


class SafetyUpsert(BaseModel):
    test_id: UUID
    requires_contrast: bool = False
    contrast_type: str | None = Field(default=None, max_length=40)
    radiation_risk: bool = False
    pregnancy_caution: bool = False
    notes: str | None = Field(default=None, max_length=2000)


class CriticalFindingIn(BaseModel):
    report_id: UUID
    summary: str = Field(min_length=5, max_length=2000)


class AckBody(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


@router.post("/contrast-check")
def contrast_check(
    payload: ContrastCheckIn,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(READ)),
):
    _ = facility_id, user
    return check_contrast_safety(db, patient_id=payload.patient_id, test_id=payload.test_id)


@router.put("/test-safety")
def put_safety(
    payload: SafetyUpsert,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(WRITE)),
):
    _ = facility_id, user
    try:
        row = upsert_test_safety(db, test_id=payload.test_id, data=payload.model_dump())
        db.commit()
        return {"test_id": str(row.test_id), "requires_contrast": row.requires_contrast, "status": row.status}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/critical-findings")
def post_critical(
    payload: CriticalFindingIn,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(WRITE)),
):
    report = db.get(ImagingReport, payload.report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="IMAGING_REPORT_NOT_FOUND")
    order = db.get(ImagingOrder, report.order_id)
    if order is None or order.facility_id != facility_id:
        raise HTTPException(status_code=404, detail="IMAGING_ORDER_NOT_FOUND")
    test = db.get(ImagingTest, order.test_id)
    try:
        finding = register_critical_finding(
            db,
            report=report,
            order=order,
            test=test,
            summary=payload.summary,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(finding.id), "status": finding.status}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/critical-findings")
def open_findings(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(READ)),
):
    _ = user
    rows = list_open_findings(db, facility_id, limit=limit)
    return [
        {
            "id": str(r.id),
            "patient_id": str(r.patient_id),
            "order_id": str(r.order_id),
            "test_name": r.test_name,
            "modality": r.modality,
            "summary": r.summary,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/critical-findings/{finding_id}/acknowledge")
def ack_finding(
    finding_id: UUID,
    body: AckBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(WRITE)),
):
    staff = _staff(db, user, facility_id)
    try:
        row = acknowledge_finding(
            db,
            finding_id=finding_id,
            facility_id=facility_id,
            staff_id=staff.id,
            note=body.note,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(row.id), "status": row.status}
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code=404 if "NOT_FOUND" in code else 400, detail=code) from exc


@router.get("/tat")
def get_tat(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(READ)),
):
    _ = user
    return imaging_tat_summary(db, facility_id, days=days)
