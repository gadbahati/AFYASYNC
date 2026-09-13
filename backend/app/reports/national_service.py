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

    facilities: list[NationalFacilitySummary] = []
    for facility in db.scalars(select(Facility).where(Facility.status == "ACTIVE").order_by(Facility.name)).all():
        facility_encounters = db.scalar(select(func.count(Encounter.id)).where(Encounter.facility_id == facility.id, Encounter.created_at >= start, Encounter.created_at < end)) or 0
        facility_invoice_totals = db.execute(select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.total_amount), 0)).where(Invoice.facility_id == facility.id, Invoice.created_at >= start, Invoice.created_at < end, Invoice.status != "VOID")).one()
        facility_payments = db.scalar(select(func.sum(Payment.amount)).where(Payment.facility_id == facility.id, Payment.created_at >= start, Payment.created_at < end, Payment.status == "CONFIRMED"))
        facility_claim_totals = db.execute(select(func.count(Claim.id), func.coalesce(func.sum(Claim.claim_amount), 0), func.coalesce(func.sum(Claim.approved_amount), 0), func.coalesce(func.sum(Claim.paid_amount), 0)).join(Invoice, Invoice.id == Claim.invoice_id).where(Invoice.facility_id == facility.id, Claim.updated_at >= start, Claim.updated_at < end)).one()
        approved, paid = _money(facility_claim_totals[2]), _money(facility_claim_totals[3])
        facilities.append(NationalFacilitySummary(facility_id=facility.id, facility_code=facility.facility_id, facility_name=facility.name, county=facility.county, encounters=int(facility_encounters), invoices=int(facility_invoice_totals[0]), billed=_money(facility_invoice_totals[1]), confirmed_payments=_money(facility_payments), claims=int(facility_claim_totals[0]), claims_amount=_money(facility_claim_totals[1]), claims_approved=approved, claims_paid=paid, claims_receivable=_money(max(approved - paid, Decimal("0")))))

    day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    open_encounters = db.scalar(select(func.count(Encounter.id)).where(Encounter.status == "OPEN", Facility.id == Encounter.facility_id, Facility.status == "ACTIVE")) or 0
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
