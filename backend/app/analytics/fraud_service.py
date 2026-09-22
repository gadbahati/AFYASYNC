"""Facility + national fraud signal detection (deterministic rules)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.models import Charge, Invoice
from app.claims.models import Claim
from app.encounters.models import Encounter


def scan_facility_fraud(db: Session, *, facility_id: UUID, days: int = 30) -> dict:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=max(1, min(days, 365)))
    signals: list[dict] = []

    # Multiple claims same invoice
    for invoice_id, count in db.execute(
        select(Claim.invoice_id, func.count())
        .select_from(Claim)
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .where(Invoice.facility_id == facility_id, Claim.created_at >= since)
        .group_by(Claim.invoice_id)
        .having(func.count() > 1)
    ).all():
        signals.append(
            {
                "code": "MULTIPLE_CLAIMS_SAME_INVOICE",
                "severity": "HIGH",
                "title": "Multiple claims for one invoice",
                "detail": f"Invoice has {count} claims in window",
                "resource_type": "INVOICE",
                "resource_id": str(invoice_id),
            }
        )

    # Same patient many claims in short window
    for patient_id, count in db.execute(
        select(Claim.patient_id, func.count())
        .select_from(Claim)
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .where(Invoice.facility_id == facility_id, Claim.created_at >= since)
        .group_by(Claim.patient_id)
        .having(func.count() >= 5)
    ).all():
        signals.append(
            {
                "code": "HIGH_CLAIM_FREQUENCY_PATIENT",
                "severity": "MEDIUM",
                "title": "High claim frequency for one patient",
                "detail": f"{count} claims in {days} days",
                "resource_type": "PATIENT",
                "resource_id": str(patient_id),
            }
        )

    # Large unpaid invoices
    for inv in db.scalars(
        select(Invoice)
        .where(
            Invoice.facility_id == facility_id,
            Invoice.total_amount >= 100_000,
            Invoice.status.notin_(["PAID", "SETTLED", "CLOSED", "CANCELLED"]),
        )
        .limit(20)
    ).all():
        signals.append(
            {
                "code": "HIGH_VALUE_OPEN_INVOICE",
                "severity": "MEDIUM",
                "title": "High-value open invoice",
                "detail": f"total={inv.total_amount} status={inv.status}",
                "resource_type": "INVOICE",
                "resource_id": str(inv.id),
            }
        )

    # Claims submitted with zero amount
    zero_claims = db.scalar(
        select(func.count())
        .select_from(Claim)
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .where(
            Invoice.facility_id == facility_id,
            Claim.created_at >= since,
            Claim.claim_amount <= 0,
        )
    ) or 0
    if zero_claims:
        signals.append(
            {
                "code": "ZERO_AMOUNT_CLAIMS",
                "severity": "LOW",
                "title": "Zero-amount claims present",
                "detail": f"{zero_claims} claims with amount <= 0",
                "resource_type": "FACILITY",
                "resource_id": str(facility_id),
            }
        )

    # Encounters without charges (capture gap — ops + fraud risk)
    enc = db.scalar(
        select(func.count()).select_from(Encounter).where(
            Encounter.facility_id == facility_id, Encounter.created_at >= since
        )
    ) or 0
    chg = db.scalar(
        select(func.count()).select_from(Charge).where(
            Charge.facility_id == facility_id, Charge.created_at >= since
        )
    ) or 0
    if enc >= 30 and chg == 0:
        signals.append(
            {
                "code": "ACTIVITY_WITHOUT_CHARGES",
                "severity": "MEDIUM",
                "title": "Encounters without charges",
                "detail": f"{enc} encounters, 0 charges in window",
                "resource_type": "FACILITY",
                "resource_id": str(facility_id),
            }
        )

    high = sum(1 for s in signals if s["severity"] == "HIGH")
    med = sum(1 for s in signals if s["severity"] == "MEDIUM")
    return {
        "facility_id": str(facility_id),
        "window_days": days,
        "scanned_at": now.isoformat(),
        "signal_count": len(signals),
        "high": high,
        "medium": med,
        "signals": signals[:100],
        "summary": f"{len(signals)} signals ({high} high, {med} medium)",
        "developer": "BAHATI GAD WANGWE",
    }
