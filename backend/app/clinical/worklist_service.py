"""Phase 139/156 — facility clinical order worklist + queue counts.

Developed by BAHATI GAD WANGWE.
"""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clinical.order_models import ClinicalOrder
from app.clinical.order_service import order_to_dict

OPEN_STATUSES = ("ORDERED", "IN_PROGRESS")
QUEUE_TYPES = ("LAB", "PHARMACY", "IMAGING")


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
        q = q.where(ClinicalOrder.status.in_(OPEN_STATUSES))
    q = q.order_by(ClinicalOrder.created_at.asc()).limit(limit)
    rows = list(db.scalars(q))
    return [order_to_dict(r) for r in rows]


def count_facility_queues(
    db: Session,
    *,
    facility_id: UUID,
) -> dict:
    """Phase 156 — open counts by department type (one query)."""
    q = (
        select(ClinicalOrder.order_type, func.count())
        .where(ClinicalOrder.facility_id == facility_id)
        .where(ClinicalOrder.status.in_(OPEN_STATUSES))
        .where(ClinicalOrder.order_type.in_(QUEUE_TYPES))
        .group_by(ClinicalOrder.order_type)
    )
    rows = list(db.execute(q).all())
    by_type = {str(t).upper(): int(c) for t, c in rows}
    counts = {t: by_type.get(t, 0) for t in QUEUE_TYPES}
    counts["total"] = sum(counts.values())
    return counts
