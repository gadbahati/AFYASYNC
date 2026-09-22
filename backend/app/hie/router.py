"""HIE depth APIs — patient summary & referral packages."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.hie.service import build_patient_summary_bundle, build_referral_package, list_export_logs
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/hie", tags=["HIE"])


class SummaryQuery(BaseModel):
    purpose: str | None = Field(default="care-coordination", max_length=200)
    destination: str | None = Field(default=None, max_length=200)


class ReferralBody(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    clinical_summary: str | None = Field(default=None, max_length=4000)
    destination: str | None = Field(default=None, max_length=200)


@router.get("/Patient/{patient_id}/$summary")
def patient_summary(
    patient_id: UUID,
    purpose: str | None = Query(default="care-coordination", max_length=200),
    destination: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.read")),
):
    try:
        bundle = build_patient_summary_bundle(
            db,
            patient_id=patient_id,
            facility_id=facility_id,
            actor_user_id=user.id,
            purpose=purpose,
            destination=destination,
        )
        db.commit()
        return bundle
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=404 if "NOT_FOUND" in code or "FACILITY" in code else 400,
            detail=code,
        ) from exc


@router.post("/referral-package")
def referral_package(
    body: ReferralBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.read")),
):
    try:
        bundle = build_referral_package(
            db,
            patient_id=body.patient_id,
            facility_id=facility_id,
            encounter_id=body.encounter_id,
            clinical_summary=body.clinical_summary,
            actor_user_id=user.id,
            destination=body.destination,
        )
        db.commit()
        return bundle
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=404 if "NOT_FOUND" in code or "FACILITY" in code else 400,
            detail=code,
        ) from exc


@router.get("/exports")
def exports(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    rows = list_export_logs(db, facility_id, limit=limit)
    return [
        {
            "id": str(r.id),
            "patient_id": str(r.patient_id),
            "export_type": r.export_type,
            "resource_count": r.resource_count,
            "purpose": r.purpose,
            "destination": r.destination,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
