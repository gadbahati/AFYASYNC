"""Phase 139/156 — clinical department worklist routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.clinical.worklist_service import count_facility_queues, list_facility_worklist
from app.database import get_db
from app.rbac.models import User

worklist_router = APIRouter(prefix="/api/v1/clinical", tags=["Clinical Worklist"])


@worklist_router.get("/worklist/counts")
def get_clinical_worklist_counts(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("clinical.record.read")),
):
    """Phase 156 — open LAB / PHARMACY / IMAGING counts in one response."""
    _ = user
    counts = count_facility_queues(db, facility_id=facility_id)
    return {
        "facility_id": str(facility_id),
        "status": "ORDERED,IN_PROGRESS",
        **counts,
        "developer": "BAHATI GAD WANGWE",
    }


@worklist_router.get("/worklist")
def get_clinical_worklist(
    order_type: str | None = Query(default=None, description="LAB | PHARMACY | IMAGING"),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("clinical.record.read")),
):
    """Facility queue of clinical orders (imaging / lab / pharmacy)."""
    _ = user
    items = list_facility_worklist(
        db,
        facility_id=facility_id,
        order_type=order_type,
        status=status,
        limit=limit,
    )
    return {
        "facility_id": str(facility_id),
        "order_type": order_type,
        "status": status or "ORDERED,IN_PROGRESS",
        "count": len(items),
        "items": items,
        "developer": "BAHATI GAD WANGWE",
    }


@worklist_router.get("/worklist/imaging")
def get_imaging_worklist(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("clinical.record.read")),
):
    """Imaging-only queue."""
    _ = user
    items = list_facility_worklist(
        db,
        facility_id=facility_id,
        order_type="IMAGING",
        status=None,
        limit=limit,
    )
    return {
        "facility_id": str(facility_id),
        "order_type": "IMAGING",
        "count": len(items),
        "items": items,
        "developer": "BAHATI GAD WANGWE",
    }
