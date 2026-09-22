"""Pharmacy & Supply OS APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.pharmacy_supply.service import list_controlled_logs, pre_dispense_check, stock_health
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/pharmacy-supply", tags=["Pharmacy Supply"])

PHARM_READ = "pharmacy.read"
PHARM_DISPENSE = "pharmacy.dispense"

# Fallbacks if RBAC uses lab-style names in some deploys
_READ_PERMS = ("pharmacy.read", "lab.order.create", "patients.record.read")


def _try_perm(name: str):
    return require_permission(name)


@router.get("/health")
def get_stock_health(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.read")),
):
    _ = user
    return stock_health(db, facility_id)


@router.get("/pre-dispense/{prescription_id}")
def check_pre_dispense(
    prescription_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.read")),
):
    _ = user
    try:
        return pre_dispense_check(db, facility_id=facility_id, prescription_id=prescription_id)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=404 if "NOT_FOUND" in code else 400,
            detail=code,
        ) from exc


@router.get("/controlled-log")
def controlled_log(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.read")),
):
    _ = user
    rows = list_controlled_logs(db, facility_id, limit=limit)
    return [
        {
            "id": str(r.id),
            "patient_id": str(r.patient_id),
            "prescription_id": str(r.prescription_id),
            "medication_id": str(r.medication_id),
            "quantity": float(r.quantity),
            "schedule_class": r.schedule_class,
            "dispensed_by": str(r.dispensed_by),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
