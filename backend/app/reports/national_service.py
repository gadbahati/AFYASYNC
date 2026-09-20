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
from app.integrations.models import Integration, IntegrationTransaction
from app.patients.models import PatientFacility
from app.pharmacy.models import InventoryItem, Prescription
from app.reports.national_schemas import (
    NationalClaimStatusSummary,
    NationalFacilitySummary,
    NationalOperationalSummary,
    NationalPayerSummary,
    NationalReport,
)


def _window(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    if end_date < start_date:
        raise ValueError("INVALID_REPORT_DATE_RANGE")
    return datetime.combine(start_date, time.min, tzinfo=timezone.utc), datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)


def _money(value: Decimal | None) -> Decimal:
    return (value or Decimal("0")).quantize(Decimal("0.01"))


def build_national_report(db: Session, start_date: date, end_date: date, *, actor_user_id: UUID) -> NationalReport:
    start, end = _window(start_date, end_date)
    active_facilities = db.scalar(select(func.count(Facility.id)).where(Facility.status == "ACTIVE")) or 0
    registered_patients = db.scalar(select(func.count(func.distinct(PatientFacility.patient_id))).join(Facility, Facility.id == PatientFacility.facility_id).where(PatientFacility.created_at >= start, PatientFacility.created_at < end, PatientFacility.status == "ACTIVE", Facility.status == "ACTIVE")) or 0
    encounters = db.scalar(select(func.count(Encounter.id)).join(Facility, Facility.id == Encounter.facility_id).where(Encounter.created_at >= start, Encounter.created_at < end, Facility.status == "ACTIVE")) or 0
    charges_total = _money(db.scalar(select(func.sum(Charge.total_amount)).join(Facility, Facility.id == Charge.facility_id).where(Charge.created_at >= start, Charge.created_at < end, Charge.status != "VOID", Facility.status == "ACTIVE")))
    invoice_totals = db.execute(select(func.coalesce(func.sum(Invoice.total_amount), 0), func.coalesce(func.sum(Invoice.payer_amount), 0), func.coalesce(func.sum(Invoice.patient_amount), 0)).join(Facility, Facility.id == Invoice.facility_id).where(Invoice.created_at >= start, Invoice.created_at < end, Invoice.status != "VOID", Facility.status == "ACTIVE")).one()
    invoices_total, payer_billed, patient_billed = map(_money, invoice_totals)
    confirmed_payments = _money(db.scalar(select(func.sum(Payment.amount)).join(Facility, Facility.id == Payment.facility_id).where(Payment.created_at >= start, Payment.created_at < end, Payment.status == "CONFIRMED", Facility.status == "ACTIVE")))

    claim_rows = db.execute(select(Claim.status, func.count(Claim.id), func.coalesce(func.sum(Claim.claim_amount), 0), func.coalesce(func.sum(Claim.approved_amount), 0), func.coalesce(func.sum(Claim.paid_amount), 0)).join(Invoice, Invoice.id == Claim.invoice_id).join(Facility, Facility.id == Invoice.facility_id).where(Claim.updated_at >= start, Claim.updated_at < end, Facility.status == "ACTIVE").group_by(Claim.status).order_by(Claim.status)).all()
    claims = sum(int(row[1]) for row in claim_rows)
    claims_amount = _money(sum((_money(row[2]) for row in claim_rows), Decimal("0")))
    claims_approved = _money(sum((_money(row[3]) for row in claim_rows), Decimal("0")))
    claims_paid = _money(sum((_money(row[4]) for row in claim_rows), Decimal("0")))
    claims_receivable = _money(max(claims_approved - claims_paid, Decimal("0")))
    claim_statuses = [NationalClaimStatusSummary(status=row[0], count=int(row[1]), amount=_money(row[2]), approved_amount=_money(row[3]), paid_amount=_money(row[4])) for row in claim_rows]

    payer_rows = db.execute(select(Payer.id, Payer.name, Payer.code, func.count(Claim.id), func.coalesce(func.sum(Claim.claim_amount), 0), func.coalesce(func.sum(Claim.approved_amount), 0), func.coalesce(func.sum(Claim.paid_amount), 0)).join(Claim, Claim.payer_id == Payer.id).join(Invoice, Invoice.id == Claim.invoice_id).join(Facility, Facility.id == Invoice.facility_id).where(Claim.updated_at >= start, Claim.updated_at < end, Facility.status == "ACTIVE").group_by(Payer.id, Payer.name, Payer.code).order_by(Payer.name)).all()
    payer_claims = [NationalPayerSummary(payer_id=row[0], payer_name=row[1], payer_code=row[2], claims=int(row[3]), amount=_money(row[4]), approved_amount=_money(row[5]), paid_amount=_money(row[6]), receivable=_money(max(_money(row[5]) - _money(row[6]), Decimal("0")))) for row in payer_rows]

    # Enumerate active facilities once, then collect period aggregates in bounded grouped
    # queries. This avoids one query per facility (N+1) while preserving the exact
    # facility-level report contract.
    facility_rows = db.execute(
        select(Facility.id, Facility.facility_id, Facility.name, Facility.county)
        .where(Facility.status == "ACTIVE")
        .order_by(Facility.name)
    ).all()
    facility_ids = [row[0] for row in facility_rows]

    encounter_by_facility = {}
    if facility_ids:
        encounter_rows = db.execute(
            select(Encounter.facility_id, func.count(Encounter.id))
            .where(
                Encounter.facility_id.in_(facility_ids),
                Encounter.created_at >= start,
                Encounter.created_at < end,
            )
            .group_by(Encounter.facility_id)
        ).all()
        encounter_by_facility = {row[0]: int(row[1]) for row in encounter_rows}

    invoice_by_facility = {}
    if facility_ids:
        invoice_rows = db.execute(
            select(
                Invoice.facility_id,
                func.count(Invoice.id),
                func.coalesce(func.sum(Invoice.total_amount), 0),
            )
            .where(
                Invoice.facility_id.in_(facility_ids),
                Invoice.created_at >= start,
                Invoice.created_at < end,
                Invoice.status != "VOID",
            )
            .group_by(Invoice.facility_id)
        ).all()
        invoice_by_facility = {
            row[0]: (int(row[1]), _money(row[2])) for row in invoice_rows
        }

    payment_by_facility = {}
    if facility_ids:
        payment_rows = db.execute(
            select(Payment.facility_id, func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.facility_id.in_(facility_ids),
                Payment.created_at >= start,
                Payment.created_at < end,
                Payment.status == "CONFIRMED",
            )
            .group_by(Payment.facility_id)
        ).all()
        payment_by_facility = {row[0]: _money(row[1]) for row in payment_rows}

    claim_by_facility = {}
    if facility_ids:
        claim_rows_by_facility = db.execute(
            select(
                Invoice.facility_id,
                func.count(Claim.id),
                func.coalesce(func.sum(Claim.claim_amount), 0),
                func.coalesce(func.sum(Claim.approved_amount), 0),
                func.coalesce(func.sum(Claim.paid_amount), 0),
            )
            .join(Invoice, Invoice.id == Claim.invoice_id)
            .where(
                Invoice.facility_id.in_(facility_ids),
                Claim.updated_at >= start,
                Claim.updated_at < end,
            )
            .group_by(Invoice.facility_id)
        ).all()
        claim_by_facility = {
            row[0]: (int(row[1]), _money(row[2]), _money(row[3]), _money(row[4]))
            for row in claim_rows_by_facility
        }

    facilities: list[NationalFacilitySummary] = []
    for facility_id, facility_code, facility_name, county in facility_rows:
        invoice_count, billed = invoice_by_facility.get(
            facility_id, (0, Decimal("0"))
        )
        claim_count, claim_amount, approved, paid = claim_by_facility.get(
            facility_id, (0, Decimal("0"), Decimal("0"), Decimal("0"))
        )
        confirmed_payments = payment_by_facility.get(facility_id, Decimal("0"))
        facilities.append(
            NationalFacilitySummary(
                facility_id=facility_id,
                facility_code=facility_code,
                facility_name=facility_name,
                county=county,
                encounters=encounter_by_facility.get(facility_id, 0),
                invoices=invoice_count,
                billed=billed,
                confirmed_payments=confirmed_payments,
                claims=claim_count,
                claims_amount=claim_amount,
                claims_approved=approved,
                claims_paid=paid,
                claims_receivable=_money(max(approved - paid, Decimal("0"))),
            )
        )

    day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    open_encounters = db.scalar(select(func.count(Encounter.id)).join(Facility, Facility.id == Encounter.facility_id).where(Encounter.status == "OPEN", Facility.status == "ACTIVE")) or 0
    encounters_24h = db.scalar(select(func.count(Encounter.id)).join(Facility, Facility.id == Encounter.facility_id).where(Encounter.created_at >= day_ago, Facility.status == "ACTIVE")) or 0
    open_invoices = db.scalar(select(func.count(Invoice.id)).join(Facility, Facility.id == Invoice.facility_id).where(Invoice.status.in_(["OPEN", "PARTIAL", "ISSUED", "PENDING"]), Facility.status == "ACTIVE")) or 0
    pending_prescriptions = db.scalar(select(func.count(Prescription.id)).join(Encounter, Encounter.id == Prescription.encounter_id).join(Facility, Facility.id == Encounter.facility_id).where(Prescription.status.in_(["PENDING", "ACTIVE", "PRESCRIBED"]), Facility.status == "ACTIVE")) or 0
    low_stock_items = db.scalar(select(func.count(InventoryItem.id)).join(Facility, Facility.id == InventoryItem.facility_id).where(InventoryItem.current_quantity <= InventoryItem.minimum_quantity, Facility.status == "ACTIVE")) or 0
    rejected_claims = db.scalar(select(func.count(Claim.id)).join(Invoice, Invoice.id == Claim.invoice_id).join(Facility, Facility.id == Invoice.facility_id).where(Claim.status.in_(["REJECTED", "DENIED"]), Facility.status == "ACTIVE")) or 0
    integration_counts = db.execute(select(IntegrationTransaction.status, func.count(IntegrationTransaction.id)).join(Integration, Integration.id == IntegrationTransaction.integration_id).join(Facility, Facility.id == Integration.facility_id).where(Facility.status == "ACTIVE", Integration.status == "ACTIVE", IntegrationTransaction.status.in_(["PENDING", "RETRYING", "FAILED"])).group_by(IntegrationTransaction.status)).all()
    integration_map = {str(status): int(count) for status, count in integration_counts}
    operations = NationalOperationalSummary(open_encounters=int(open_encounters), encounters_24h=int(encounters_24h), open_invoices=int(open_invoices), pending_prescriptions=int(pending_prescriptions), low_stock_items=int(low_stock_items), rejected_claims=int(rejected_claims), integration_pending=integration_map.get("PENDING", 0), integration_retrying=integration_map.get("RETRYING", 0), integration_failed=integration_map.get("FAILED", 0))

    record_audit(db, action="VIEW_NATIONAL_REPORT", resource_type="NATIONAL_REPORT", result="SUCCESS", user_id=actor_user_id, metadata={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()})
    return NationalReport(start_date=start_date, end_date=end_date, active_facilities=int(active_facilities), registered_patients=int(registered_patients), encounters=int(encounters), charges_total=charges_total, invoices_total=invoices_total, payer_billed=payer_billed, patient_billed=patient_billed, confirmed_payments=confirmed_payments, claims=claims, claims_amount=claims_amount, claims_approved=claims_approved, claims_paid=claims_paid, claims_receivable=claims_receivable, claim_statuses=claim_statuses, payer_claims=payer_claims, facilities=facilities, operations=operations)
