"""Claims pipeline KPIs for facility and government oversight."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.models import Invoice
from app.claims.models import Claim


def claims_kpis(db: Session, *, facility_id: UUID, days: int = 30) -> dict:
    days = max(1, min(days, 365))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    by_status = {
        str(s): int(c)
        for s, c in db.execute(
            select(Claim.status, func.count())
            .select_from(Claim)
            .join(Invoice, Invoice.id == Claim.invoice_id)
            .where(Invoice.facility_id == facility_id, Claim.created_at >= since)
            .group_by(Claim.status)
        ).all()
    }

    total = sum(by_status.values())
    amount = db.scalar(
        select(func.coalesce(func.sum(Claim.claim_amount), 0))
        .select_from(Claim)
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .where(Invoice.facility_id == facility_id, Claim.created_at >= since)
    )

    denied = by_status.get("DENIED", 0) + by_status.get("REJECTED", 0)
    paid = by_status.get("PAID", 0) + by_status.get("SETTLED", 0)
    submitted = by_status.get("SUBMITTED", 0) + by_status.get("IN_REVIEW", 0)

    denial_rate = round(denied / total, 4) if total else 0.0

    return {
        "facility_id": str(facility_id),
        "window_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claims_total": total,
        "claim_amount_sum": float(amount or 0),
        "by_status": by_status,
        "submitted_open": submitted,
        "paid_or_settled": paid,
        "denied_or_rejected": denied,
        "denial_rate": denial_rate,
        "developer": "BAHATI GAD WANGWE",
    }
