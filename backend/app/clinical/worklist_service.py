"""Phase 139 — facility clinical order worklist (lab/pharmacy/imaging).

Developed by BAHATI GAD WANGWE.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clinical.order_models import ClinicalOrder
from app.clinical.order_service import order_to_dict


def list_facility_worklist(
    db: Session,
    *,
    facility_id: UUID,
    order_type: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Open clinical orders for the facility (department queues)."""
    limit = max(1, min(int(limit or 100), 500))
    q = select(ClinicalOrder).where(ClinicalOrder.facility_id == facility_id)
    if order_type:
        q = q.where(ClinicalOrder.order_type == order_type.strip().upper())
    if status:
        q = q.where(ClinicalOrder.status == status.strip().upper())
    else:
        # Default: actionable queue
        q = q.where(ClinicalOrder.status.in_(("ORDERED", "IN_PROGRESS")))
    q = q.order_by(ClinicalOrder.created_at.asc()).limit(limit)
    rows = list(db.scalars(q))
    return [order_to_dict(r) for r in rows]
