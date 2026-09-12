from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Charge, Invoice, Payment
from app.claims.models import Claim
from app.encounters.models import Encounter
from app.patients.models import PatientFacility


def _window(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    if end_date < start_date:
        raise ValueError("INVALID_REPORT_DATE_RANGE")
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
    return start, end


def build_facility_report(
    db: Session,
    facility_id: UUID,
    start_date: date,
    end_date: date,
    *,
    actor_user_id: UUID | None = None,
) -> dict[str, object]:
    start, end = _window(start_date, end_date)

    patients = int(
        db.scalar(
            select(func.count(PatientFacility.id)).where(
                PatientFacility.facility_id == facility_id,
                PatientFacility.created_at >= start,
                PatientFacility.created_at <= end,
            )
        )
        or 0
    )
    encounters = int(
        db.scalar(
            select(func.count(Encounter.id)).where(
                Encounter.facility_id == facility_id,
                Encounter.created_at >= start,
                Encounter.created_at <= end,
            )
        )
        or 0
    )
    charges_total = Decimal(
        str(
            db.scalar(
                select(func.coalesce(func.sum(Charge.total_amount), 0)).where(
                    Charge.facility_id == facility_id,
                    Charge.created_at >= start,
                    Charge.created_at <= end,
                    Charge.status == "ACTIVE",
                )
            )
            or 0
        )
    ).quantize(Decimal("0.01"))

    invoice_totals = db.execute(
        select(
            func.coalesce(func.sum(Invoice.total_amount), 0),
            func.coalesce(func.sum(Invoice.payer_amount), 0),
            func.coalesce(func.sum(Invoice.patient_amount), 0),
        ).where(
            Invoice.facility_id == facility_id,
            Invoice.created_at >= start,
            Invoice.created_at <= end,
            Invoice.status != "VOID",
        )
    ).one()
    invoices_total = Decimal(str(invoice_totals[0])).quantize(Decimal("0.01"))
    payer_billed = Decimal(str(invoice_totals[1])).quantize(Decimal("0.01"))
    patient_billed = Decimal(str(invoice_totals[2])).quantize(Decimal("0.01"))

    confirmed_payments = Decimal(
        str(
            db.scalar(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(
                    Payment.facility_id == facility_id,
                    Payment.created_at >= start,
                    Payment.created_at <= end,
                    Payment.status == "CONFIRMED",
                )
            )
            or 0
        )
    ).quantize(Decimal("0.01"))

    claim_totals = db.execute(
        select(
            func.count(Claim.id),
            func.coalesce(func.sum(Claim.claim_amount), 0),
            func.coalesce(func.sum(Claim.approved_amount), 0),
            func.coalesce(func.sum(Claim.paid_amount), 0),
        ).join(Invoice, Invoice.id == Claim.invoice_id).where(
            Invoice.facility_id == facility_id,
            Claim.updated_at >= start,
            Claim.updated_at <= end,
        )
    ).one()

    claims = int(claim_totals[0] or 0)
    claims_amount = Decimal(str(claim_totals[1] or 0)).quantize(Decimal("0.01"))
    claims_approved = Decimal(str(claim_totals[2] or 0)).quantize(Decimal("0.01"))
    claims_paid = Decimal(str(claim_totals[3] or 0)).quantize(Decimal("0.01"))

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
    }
