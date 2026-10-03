"""Phase 91 — Aggregate operational metrics across the resolved operating scope.

Facility-level reports remain the unit of operational truth. This module sums
a small set of safe aggregates across every facility the caller is authorized
to see under the selected scope (facility | network | county | national).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.models import Charge, Invoice, Payment
from app.claims.models import Claim
from app.context.service import resolve_facility_ids
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.patients.models import PatientFacility
from app.rbac.models import User


def _window(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    if end_date < start_date or (end_date - start_date).days > 365:
        raise ValueError("INVALID_REPORT_DATE_RANGE")
    return (
        datetime.combine(start_date, time.min, tzinfo=timezone.utc),
        datetime.combine(end_date, time.max, tzinfo=timezone.utc),
    )


def _money(value: object) -> str:
    return str(Decimal(str(value or 0)).quantize(Decimal("0.01")))


def build_scoped_operations_summary(
    db: Session,
    *,
    user: User,
    token_facility_id: UUID,
    scope: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=29))
    start_dt, end_dt = _window(start, end)

    facility_ids = resolve_facility_ids(
        db, user=user, token_facility_id=token_facility_id, scope=scope
    )
    if not facility_ids:
        facility_ids = [token_facility_id]

    patients = int(
        db.scalar(
            select(func.count(func.distinct(PatientFacility.patient_id))).where(
                PatientFacility.facility_id.in_(facility_ids),
                PatientFacility.status == "ACTIVE",
                PatientFacility.created_at >= start_dt,
                PatientFacility.created_at <= end_dt,
            )
        )
        or 0
    )
    encounters = int(
        db.scalar(
            select(func.count(Encounter.id)).where(
                Encounter.facility_id.in_(facility_ids),
                Encounter.created_at >= start_dt,
                Encounter.created_at <= end_dt,
            )
        )
        or 0
    )
    charges_total = db.scalar(
        select(func.coalesce(func.sum(Charge.total_amount), 0)).where(
            Charge.facility_id.in_(facility_ids),
            Charge.created_at >= start_dt,
            Charge.created_at <= end_dt,
            Charge.status == "ACTIVE",
        )
    )
    invoices_total = db.scalar(
        select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
            Invoice.facility_id.in_(facility_ids),
            Invoice.created_at >= start_dt,
            Invoice.created_at <= end_dt,
            Invoice.status != "VOID",
        )
    )
    payments_total = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.facility_id.in_(facility_ids),
            Payment.created_at >= start_dt,
            Payment.created_at <= end_dt,
            Payment.status == "CONFIRMED",
        )
    )
    claim_row = db.execute(
        select(
            func.count(Claim.id),
            func.coalesce(func.sum(Claim.claim_amount), 0),
            func.coalesce(func.sum(Claim.approved_amount), 0),
            func.coalesce(func.sum(Claim.paid_amount), 0),
        )
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .where(
            Invoice.facility_id.in_(facility_ids),
            Claim.updated_at >= start_dt,
            Claim.updated_at <= end_dt,
        )
    ).one()

    facilities = list(
        db.scalars(select(Facility).where(Facility.id.in_(facility_ids)).limit(100)).all()
    )

    return {
        "scope": scope,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "facility_count": len(facility_ids),
        "token_facility_id": str(token_facility_id),
        "facilities": [
            {
                "id": str(f.id),
                "name": f.name,
                "county": f.county,
                "status": f.status,
            }
            for f in facilities
        ],
        "metrics": {
            "patients": patients,
            "encounters": encounters,
            "charges_total": _money(charges_total),
            "invoices_total": _money(invoices_total),
            "confirmed_payments": _money(payments_total),
            "claims": int(claim_row[0] or 0),
            "claims_amount": _money(claim_row[1]),
            "claims_approved": _money(claim_row[2]),
            "claims_paid": _money(claim_row[3]),
        },
        "note": (
            "Aggregates cover facilities authorized under the selected operating scope. "
            "Per-facility operational detail remains available via /api/v1/reports/facility."
        ),
        "developer": "BAHATI GAD WANGWE",
    }
