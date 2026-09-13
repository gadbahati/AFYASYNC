from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Charge, Invoice, Payment
from app.claims.models import Claim
from app.coverage.models import Payer
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.patients.models import PatientFacility
from app.reports.national_schemas import (
    NationalClaimStatusSummary,
    NationalFacilitySummary,
    NationalPayerSummary,
    NationalReport,
)


def _window(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    if end_date < start_date:
        raise ValueError("INVALID_REPORT_DATE_RANGE")
    return (
        datetime.combine(start_date, time.min, tzinfo=timezone.utc),
        datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


def _money(value: Decimal | None) -> Decimal:
    return (value or Decimal("0")).quantize(Decimal("0.01"))


def build_national_report(
    db: Session,
    start_date: date,
    end_date: date,
    *,
    actor_user_id: UUID,
) -> NationalReport:
    start, end = _window(start_date, end_date)

    active_facilities = db.scalar(
        select(func.count(Facility.id)).where(Facility.status == "ACTIVE")
    ) or 0

    registered_patients = db.scalar(
        select(func.count(func.distinct(PatientFacility.patient_id)))
        .join(Facility, Facility.id == PatientFacility.facility_id)
        .where(
            PatientFacility.created_at >= start,
            PatientFacility.created_at < end,
            PatientFacility.status == "ACTIVE",
            Facility.status == "ACTIVE",
        )
    ) or 0

    encounters = db.scalar(
        select(func.count(Encounter.id))
        .join(Facility, Facility.id == Encounter.facility_id)
        .where(
            Encounter.created_at >= start,
            Encounter.created_at < end,
            Facility.status == "ACTIVE",
        )
    ) or 0

    charges_total = _money(db.scalar(
        select(func.sum(Charge.total_amount))
        .join(Facility, Facility.id == Charge.facility_id)
        .where(
            Charge.created_at >= start,
            Charge.created_at < end,
            Charge.status != "VOID",
            Facility.status == "ACTIVE",
        )
    ))

    invoice_totals = db.execute(
        select(
            func.coalesce(func.sum(Invoice.total_amount), 0),
            func.coalesce(func.sum(Invoice.payer_amount), 0),
            func.coalesce(func.sum(Invoice.patient_amount), 0),
        )
        .join(Facility, Facility.id == Invoice.facility_id)
        .where(
            Invoice.created_at >= start,
            Invoice.created_at < end,
            Invoice.status != "VOID",
            Facility.status == "ACTIVE",
        )
    ).one()
    invoices_total = _money(invoice_totals[0])
    payer_billed = _money(invoice_totals[1])
    patient_billed = _money(invoice_totals[2])

    confirmed_payments = _money(db.scalar(
        select(func.sum(Payment.amount))
        .join(Facility, Facility.id == Payment.facility_id)
        .where(
            Payment.created_at >= start,
            Payment.created_at < end,
            Payment.status == "CONFIRMED",
            Facility.status == "ACTIVE",
        )
    ))

    claim_rows = db.execute(
        select(
            Claim.status,
            func.count(Claim.id),
            func.coalesce(func.sum(Claim.claim_amount), 0),
            func.coalesce(func.sum(Claim.approved_amount), 0),
            func.coalesce(func.sum(Claim.paid_amount), 0),
        )
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .join(Facility, Facility.id == Invoice.facility_id)
        .where(
            Claim.updated_at >= start,
            Claim.updated_at < end,
            Facility.status == "ACTIVE",
        )
        .group_by(Claim.status)
        .order_by(Claim.status)
    ).all()

    claims = sum(int(row[1]) for row in claim_rows)
    claims_amount = _money(sum((_money(row[2]) for row in claim_rows), Decimal("0")))
    claims_approved = _money(sum((_money(row[3]) for row in claim_rows), Decimal("0")))
    claims_paid = _money(sum((_money(row[4]) for row in claim_rows), Decimal("0")))
    claims_receivable = _money(max(claims_approved - claims_paid, Decimal("0")))
    claim_statuses = [
        NationalClaimStatusSummary(
            status=row[0],
            count=int(row[1]),
            amount=_money(row[2]),
            approved_amount=_money(row[3]),
            paid_amount=_money(row[4]),
        )
        for row in claim_rows
    ]

    payer_rows = db.execute(
        select(
            Payer.id,
            Payer.name,
            Payer.code,
            func.count(Claim.id),
            func.coalesce(func.sum(Claim.claim_amount), 0),
            func.coalesce(func.sum(Claim.approved_amount), 0),
            func.coalesce(func.sum(Claim.paid_amount), 0),
        )
        .join(Claim, Claim.payer_id == Payer.id)
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .join(Facility, Facility.id == Invoice.facility_id)
        .where(
            Claim.updated_at >= start,
            Claim.updated_at < end,
            Facility.status == "ACTIVE",
        )
        .group_by(Payer.id, Payer.name, Payer.code)
        .order_by(Payer.name)
    ).all()
    payer_claims = [
        NationalPayerSummary(
            payer_id=row[0],
            payer_name=row[1],
            payer_code=row[2],
            claims=int(row[3]),
            amount=_money(row[4]),
            approved_amount=_money(row[5]),
            paid_amount=_money(row[6]),
            receivable=_money(max(_money(row[5]) - _money(row[6]), Decimal("0"))),
        )
        for row in payer_rows
    ]

    facility_rows = db.execute(
        select(
            Facility.id,
            Facility.facility_id,
            Facility.name,
            Facility.county,
            func.count(func.distinct(Encounter.id)),
            func.count(func.distinct(Invoice.id)),
            func.coalesce(func.sum(Invoice.total_amount), 0),
            func.coalesce(func.sum(func.case((Payment.status == "CONFIRMED", Payment.amount), else_=0)), 0),
            func.count(func.distinct(Claim.id)),
            func.coalesce(func.sum(Claim.claim_amount), 0),
            func.coalesce(func.sum(Claim.approved_amount), 0),
            func.coalesce(func.sum(Claim.paid_amount), 0),
        )
        .outerjoin(Encounter, (Encounter.facility_id == Facility.id) & (Encounter.created_at >= start) & (Encounter.created_at < end))
        .outerjoin(Invoice, (Invoice.facility_id == Facility.id) & (Invoice.created_at >= start) & (Invoice.created_at < end) & (Invoice.status != "VOID"))
        .outerjoin(Payment, (Payment.facility_id == Facility.id) & (Payment.created_at >= start) & (Payment.created_at < end))
        .outerjoin(Claim, (Claim.invoice_id == Invoice.id) & (Claim.updated_at >= start) & (Claim.updated_at < end))
        .where(Facility.status == "ACTIVE")
        .group_by(Facility.id, Facility.facility_id, Facility.name, Facility.county)
        .order_by(Facility.name)
    ).all()

    facilities = [
        NationalFacilitySummary(
            facility_id=row[0],
            facility_code=row[1],
            facility_name=row[2],
            county=row[3],
            encounters=int(row[4]),
            invoices=int(row[5]),
            billed=_money(row[6]),
            confirmed_payments=_money(row[7]),
            claims=int(row[8]),
            claims_amount=_money(row[9]),
            claims_approved=_money(row[10]),
            claims_paid=_money(row[11]),
            claims_receivable=_money(max(_money(row[10]) - _money(row[11]), Decimal("0"))),
        )
        for row in facility_rows
    ]

    record_audit(
        db,
        action="VIEW_NATIONAL_REPORT",
        resource_type="NATIONAL_REPORT",
        result="SUCCESS",
        user_id=actor_user_id,
        metadata={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
    )

    return NationalReport(
        start_date=start_date,
        end_date=end_date,
        active_facilities=int(active_facilities),
        registered_patients=int(registered_patients),
        encounters=int(encounters),
        charges_total=charges_total,
        invoices_total=invoices_total,
        payer_billed=payer_billed,
        patient_billed=patient_billed,
        confirmed_payments=confirmed_payments,
        claims=claims,
        claims_amount=claims_amount,
        claims_approved=claims_approved,
        claims_paid=claims_paid,
        claims_receivable=claims_receivable,
        claim_statuses=claim_statuses,
        payer_claims=payer_claims,
        facilities=facilities,
    )
