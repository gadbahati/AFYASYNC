from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Charge, Invoice, Payment
from app.claims.models import Claim
from app.coverage.models import Payer
from app.encounters.models import Encounter
from app.patients.models import PatientFacility


def _window(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    if end_date < start_date:
        raise ValueError("INVALID_REPORT_DATE_RANGE")
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
    return start, end


def _money(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def build_facility_report(
    db: Session,
    facility_id: UUID,
    start_date: date,
    end_date: date,
    *,
    actor_user_id: UUID | None = None,
) -> dict[str, object]:
    start, end = _window(start_date, end_date)

    patients = int(db.scalar(select(func.count(PatientFacility.id)).where(
        PatientFacility.facility_id == facility_id,
        PatientFacility.created_at >= start,
        PatientFacility.created_at <= end,
    )) or 0)
    encounters = int(db.scalar(select(func.count(Encounter.id)).where(
        Encounter.facility_id == facility_id,
        Encounter.created_at >= start,
        Encounter.created_at <= end,
    )) or 0)
    charges_total = _money(db.scalar(select(func.coalesce(func.sum(Charge.total_amount), 0)).where(
        Charge.facility_id == facility_id,
        Charge.created_at >= start,
        Charge.created_at <= end,
        Charge.status == "ACTIVE",
    )))

    invoice_totals = db.execute(select(
        func.coalesce(func.sum(Invoice.total_amount), 0),
        func.coalesce(func.sum(Invoice.payer_amount), 0),
        func.coalesce(func.sum(Invoice.patient_amount), 0),
    ).where(
        Invoice.facility_id == facility_id,
        Invoice.created_at >= start,
        Invoice.created_at <= end,
        Invoice.status != "VOID",
    )).one()
    invoices_total = _money(invoice_totals[0])
    payer_billed = _money(invoice_totals[1])
    patient_billed = _money(invoice_totals[2])

    confirmed_payments = _money(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.facility_id == facility_id,
        Payment.created_at >= start,
        Payment.created_at <= end,
        Payment.status == "CONFIRMED",
    )))

    claim_filter = (
        Claim.updated_at >= start,
        Claim.updated_at <= end,
        Invoice.facility_id == facility_id,
    )
    claim_totals = db.execute(select(
        func.count(Claim.id),
        func.coalesce(func.sum(Claim.claim_amount), 0),
        func.coalesce(func.sum(Claim.approved_amount), 0),
        func.coalesce(func.sum(Claim.paid_amount), 0),
    ).join(Invoice, Invoice.id == Claim.invoice_id).where(*claim_filter)).one()

    claims = int(claim_totals[0] or 0)
    claims_amount = _money(claim_totals[1])
    claims_approved = _money(claim_totals[2])
    claims_paid = _money(claim_totals[3])
    claims_receivable = max(claims_approved - claims_paid, Decimal("0.00"))

    status_rows = db.execute(select(
        Claim.status,
        func.count(Claim.id),
        func.coalesce(func.sum(Claim.claim_amount), 0),
        func.coalesce(func.sum(Claim.approved_amount), 0),
        func.coalesce(func.sum(Claim.paid_amount), 0),
    ).join(Invoice, Invoice.id == Claim.invoice_id).where(*claim_filter).group_by(Claim.status).order_by(Claim.status)).all()
    claim_statuses = [
        {
            "status": row[0],
            "count": int(row[1] or 0),
            "amount": _money(row[2]),
            "approved_amount": _money(row[3]),
            "paid_amount": _money(row[4]),
        }
        for row in status_rows
    ]

    payer_rows = db.execute(select(
        Payer.id,
        Payer.name,
        Payer.code,
        func.count(Claim.id),
        func.coalesce(func.sum(Claim.claim_amount), 0),
        func.coalesce(func.sum(Claim.approved_amount), 0),
        func.coalesce(func.sum(Claim.paid_amount), 0),
    ).join(Invoice, Invoice.id == Claim.invoice_id)
     .join(Payer, Payer.id == Claim.payer_id)
     .where(*claim_filter)
     .group_by(Payer.id, Payer.name, Payer.code)
     .order_by(func.sum(Claim.claim_amount).desc(), Payer.name)).all()
    payer_claims = []
    for row in payer_rows:
        approved = _money(row[5])
        paid = _money(row[6])
        payer_claims.append({
            "payer_id": str(row[0]),
            "payer_name": row[1],
            "payer_code": row[2],
            "claims": int(row[3] or 0),
            "amount": _money(row[4]),
            "approved_amount": approved,
            "paid_amount": paid,
            "receivable": max(approved - paid, Decimal("0.00")),
        })

    record_audit(
        db,
        action="VIEW_FACILITY_REPORT",
        resource_type="FACILITY_REPORT",
        resource_id=str(facility_id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        commit=True,
    )

    return {
        "facility_id": str(facility_id),
        "start_date": start_date,
        "end_date": end_date,
        "patients": patients,
        "encounters": encounters,
        "charges_total": charges_total,
        "invoices_total": invoices_total,
        "payer_billed": payer_billed,
        "patient_billed": patient_billed,
        "confirmed_payments": confirmed_payments,
        "claims": claims,
        "claims_amount": claims_amount,
        "claims_approved": claims_approved,
        "claims_paid": claims_paid,
        "claims_receivable": claims_receivable,
        "claim_statuses": claim_statuses,
        "payer_claims": payer_claims,
    }
