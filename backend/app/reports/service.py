from datetime import date, datetime, time, timezone, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admissions.models import Admission
from app.audit.service import record_audit
from app.billing.models import Charge, Invoice, Payment
from app.claims.models import Claim
from app.coverage.models import Payer
from app.encounters.models import Encounter
from app.patients.models import PatientFacility
from app.pharmacy.models import InventoryItem, Prescription, StockMovement
from app.clinical.models import Diagnosis
from app.referrals.models import Referral


def _window(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    if end_date < start_date:
        raise ValueError("INVALID_REPORT_DATE_RANGE")
    return datetime.combine(start_date, time.min, tzinfo=timezone.utc), datetime.combine(end_date, time.max, tzinfo=timezone.utc)


def _money(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _audit_report(db: Session, *, action: str, facility_id: UUID, start_date: date, end_date: date, actor_user_id: UUID | None) -> None:
    try:
        record_audit(db, action=action, resource_type=action.removeprefix("VIEW_") or "REPORT", resource_id=str(facility_id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, metadata={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}, commit=True)
    except Exception:
        db.rollback()


def build_facility_report(db: Session, facility_id: UUID, start_date: date, end_date: date, *, actor_user_id: UUID | None = None) -> dict[str, object]:
    start, end = _window(start_date, end_date)
    patients = int(db.scalar(select(func.count(PatientFacility.id)).where(PatientFacility.facility_id == facility_id, PatientFacility.created_at >= start, PatientFacility.created_at <= end)) or 0)
    encounters = int(db.scalar(select(func.count(Encounter.id)).where(Encounter.facility_id == facility_id, Encounter.created_at >= start, Encounter.created_at <= end)) or 0)
    charges_total = _money(db.scalar(select(func.coalesce(func.sum(Charge.total_amount), 0)).where(Charge.facility_id == facility_id, Charge.created_at >= start, Charge.created_at <= end, Charge.status == "ACTIVE")))
    invoice_totals = db.execute(select(func.coalesce(func.sum(Invoice.total_amount), 0), func.coalesce(func.sum(Invoice.payer_amount), 0), func.coalesce(func.sum(Invoice.patient_amount), 0)).where(Invoice.facility_id == facility_id, Invoice.created_at >= start, Invoice.created_at <= end, Invoice.status != "VOID")).one()
    invoices_total, payer_billed, patient_billed = _money(invoice_totals[0]), _money(invoice_totals[1]), _money(invoice_totals[2])
    confirmed_payments = _money(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.facility_id == facility_id, Payment.created_at >= start, Payment.created_at <= end, Payment.status == "CONFIRMED")))
    claim_filter = (Claim.updated_at >= start, Claim.updated_at <= end, Invoice.facility_id == facility_id)
    claim_totals = db.execute(select(func.count(Claim.id), func.coalesce(func.sum(Claim.claim_amount), 0), func.coalesce(func.sum(Claim.approved_amount), 0), func.coalesce(func.sum(Claim.paid_amount), 0)).join(Invoice, Invoice.id == Claim.invoice_id).where(*claim_filter)).one()
    claims, claims_amount, claims_approved, claims_paid = int(claim_totals[0] or 0), _money(claim_totals[1]), _money(claim_totals[2]), _money(claim_totals[3])
    status_rows = db.execute(select(Claim.status, func.count(Claim.id), func.coalesce(func.sum(Claim.claim_amount), 0), func.coalesce(func.sum(Claim.approved_amount), 0), func.coalesce(func.sum(Claim.paid_amount), 0)).join(Invoice, Invoice.id == Claim.invoice_id).where(*claim_filter).group_by(Claim.status).order_by(Claim.status)).all()
    claim_statuses = [{"status": r[0] or "UNKNOWN", "count": int(r[1] or 0), "amount": _money(r[2]), "approved_amount": _money(r[3]), "paid_amount": _money(r[4])} for r in status_rows]
    payer_rows = db.execute(select(Payer.id, Payer.name, Payer.code, func.count(Claim.id), func.coalesce(func.sum(Claim.claim_amount), 0), func.coalesce(func.sum(Claim.approved_amount), 0), func.coalesce(func.sum(Claim.paid_amount), 0)).join(Invoice, Invoice.id == Claim.invoice_id).join(Payer, Payer.id == Claim.payer_id).where(*claim_filter).group_by(Payer.id, Payer.name, Payer.code).order_by(func.sum(Claim.claim_amount).desc(), Payer.name)).all()
    payer_claims = [{"payer_id": str(r[0]), "payer_name": r[1] or "Unknown payer", "payer_code": r[2] or "", "claims": int(r[3] or 0), "amount": _money(r[4]), "approved_amount": _money(r[5]), "paid_amount": _money(r[6]), "receivable": max(_money(r[5]) - _money(r[6]), Decimal("0.00"))} for r in payer_rows]
    _audit_report(db, action="VIEW_FACILITY_REPORT", facility_id=facility_id, start_date=start_date, end_date=end_date, actor_user_id=actor_user_id)
    return {"facility_id": str(facility_id), "start_date": start_date, "end_date": end_date, "patients": patients, "encounters": encounters, "charges_total": charges_total, "invoices_total": invoices_total, "payer_billed": payer_billed, "patient_billed": patient_billed, "confirmed_payments": confirmed_payments, "claims": claims, "claims_amount": claims_amount, "claims_approved": claims_approved, "claims_paid": claims_paid, "claims_receivable": max(claims_approved - claims_paid, Decimal("0.00")), "claim_statuses": claim_statuses, "payer_claims": payer_claims}


def build_facility_operations_report(db: Session, facility_id: UUID, start_date: date, end_date: date, *, actor_user_id: UUID | None = None) -> dict[str, object]:
    """Build a real facility report using bounded aggregate queries.

    The daily section is assembled from grouped queries rather than running a
    separate set of database queries for every calendar day. This keeps a
    monthly report fast and avoids connection/request exhaustion.
    """
    start, end = _window(start_date, end_date)
    enc_filter = (Encounter.facility_id == facility_id, Encounter.created_at >= start, Encounter.created_at <= end)

    patients = int(db.scalar(select(func.count(PatientFacility.id)).where(PatientFacility.facility_id == facility_id, PatientFacility.created_at >= start, PatientFacility.created_at <= end)) or 0)
    encounters = int(db.scalar(select(func.count(Encounter.id)).where(*enc_filter)) or 0)
    diagnoses = int(db.scalar(select(func.count(Diagnosis.id)).join(Encounter, Encounter.id == Diagnosis.encounter_id).where(*enc_filter)) or 0)
    prescriptions = int(db.scalar(select(func.count(Prescription.id)).join(Encounter, Encounter.id == Prescription.encounter_id).where(*enc_filter)) or 0)
    admissions = int(db.scalar(select(func.count(Admission.id)).where(Admission.facility_id == facility_id, Admission.created_at >= start, Admission.created_at <= end)) or 0)
    referrals = int(db.scalar(select(func.count(Referral.id)).where(Referral.source_facility_id == facility_id, Referral.created_at >= start, Referral.created_at <= end)) or 0)
    charges_total = _money(db.scalar(select(func.coalesce(func.sum(Charge.total_amount), 0)).where(Charge.facility_id == facility_id, Charge.created_at >= start, Charge.created_at <= end, Charge.status == "ACTIVE")))
    invoices_total = _money(db.scalar(select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(Invoice.facility_id == facility_id, Invoice.created_at >= start, Invoice.created_at <= end, Invoice.status != "VOID")))
    confirmed_payments = _money(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.facility_id == facility_id, Payment.created_at >= start, Payment.created_at <= end, Payment.status == "CONFIRMED")))

    movement_rows = db.execute(select(StockMovement.movement_type, func.coalesce(func.sum(StockMovement.quantity), 0)).join(InventoryItem, InventoryItem.id == StockMovement.inventory_item_id).where(InventoryItem.facility_id == facility_id, StockMovement.created_at >= start, StockMovement.created_at <= end).group_by(StockMovement.movement_type)).all()
    received = sum((Decimal(str(q or 0)) for t, q in movement_rows if t in {"RECEIVE", "RECEIPT"}), Decimal("0.00"))
    dispensed = sum((Decimal(str(q or 0)) for t, q in movement_rows if t in {"DISPENSE", "ISSUE"}), Decimal("0.00"))

    diagnosis_rows = db.execute(select(Diagnosis.diagnosis_name, func.count(Diagnosis.id)).join(Encounter, Encounter.id == Diagnosis.encounter_id).where(*enc_filter).group_by(Diagnosis.diagnosis_name).order_by(func.count(Diagnosis.id).desc(), Diagnosis.diagnosis_name).limit(20)).all()
    top_diagnoses = [{"diagnosis": r[0] or "Unspecified", "count": int(r[1] or 0)} for r in diagnosis_rows]

    daily_dates: list[date] = []
    cursor = start_date
    while cursor <= end_date:
        daily_dates.append(cursor)
        cursor += timedelta(days=1)

    daily: dict[date, dict[str, object]] = {d: {"date": d, "patients": 0, "encounters": 0, "diagnoses": 0, "prescriptions": 0, "admissions": 0, "referrals": 0, "charges": Decimal("0.00"), "invoices": Decimal("0.00"), "payments": Decimal("0.00"), "stock_received_quantity": Decimal("0.00"), "stock_dispensed_quantity": Decimal("0.00")} for d in daily_dates}

    def day_key(value: object) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    grouped_queries = [
        (select(func.date(PatientFacility.created_at), func.count(PatientFacility.id)).where(PatientFacility.facility_id == facility_id, PatientFacility.created_at >= start, PatientFacility.created_at <= end).group_by(func.date(PatientFacility.created_at)), "patients"),
        (select(func.date(Encounter.created_at), func.count(Encounter.id)).where(*enc_filter).group_by(func.date(Encounter.created_at)), "encounters"),
        (select(func.date(Diagnosis.created_at), func.count(Diagnosis.id)).join(Encounter, Encounter.id == Diagnosis.encounter_id).where(*enc_filter).group_by(func.date(Diagnosis.created_at)), "diagnoses"),
        (select(func.date(Prescription.created_at), func.count(Prescription.id)).join(Encounter, Encounter.id == Prescription.encounter_id).where(*enc_filter).group_by(func.date(Prescription.created_at)), "prescriptions"),
        (select(func.date(Admission.created_at), func.count(Admission.id)).where(Admission.facility_id == facility_id, Admission.created_at >= start, Admission.created_at <= end).group_by(func.date(Admission.created_at)), "admissions"),
        (select(func.date(Referral.created_at), func.count(Referral.id)).where(Referral.source_facility_id == facility_id, Referral.created_at >= start, Referral.created_at <= end).group_by(func.date(Referral.created_at)), "referrals"),
    ]
    for statement, field in grouped_queries:
        for day, count in db.execute(statement).all():
            key = day_key(day)
            if key in daily:
                daily[key][field] = int(count or 0)

    money_queries = [
        (select(func.date(Charge.created_at), func.coalesce(func.sum(Charge.total_amount), 0)).where(Charge.facility_id == facility_id, Charge.created_at >= start, Charge.created_at <= end, Charge.status == "ACTIVE").group_by(func.date(Charge.created_at)), "charges"),
        (select(func.date(Invoice.created_at), func.coalesce(func.sum(Invoice.total_amount), 0)).where(Invoice.facility_id == facility_id, Invoice.created_at >= start, Invoice.created_at <= end, Invoice.status != "VOID").group_by(func.date(Invoice.created_at)), "invoices"),
        (select(func.date(Payment.created_at), func.coalesce(func.sum(Payment.amount), 0)).where(Payment.facility_id == facility_id, Payment.created_at >= start, Payment.created_at <= end, Payment.status == "CONFIRMED").group_by(func.date(Payment.created_at)), "payments"),
    ]
    for statement, field in money_queries:
        for day, amount in db.execute(statement).all():
            key = day_key(day)
            if key in daily:
                daily[key][field] = _money(amount)

    for day, movement_type, quantity in db.execute(select(func.date(StockMovement.created_at), StockMovement.movement_type, func.coalesce(func.sum(StockMovement.quantity), 0)).join(InventoryItem, InventoryItem.id == StockMovement.inventory_item_id).where(InventoryItem.facility_id == facility_id, StockMovement.created_at >= start, StockMovement.created_at <= end).group_by(func.date(StockMovement.created_at), StockMovement.movement_type)).all():
        key = day_key(day)
        if key not in daily:
            continue
        quantity_decimal = Decimal(str(quantity or 0))
        if movement_type in {"RECEIVE", "RECEIPT"}:
            daily[key]["stock_received_quantity"] = daily[key]["stock_received_quantity"] + quantity_decimal
        elif movement_type in {"DISPENSE", "ISSUE"}:
            daily[key]["stock_dispensed_quantity"] = daily[key]["stock_dispensed_quantity"] + quantity_decimal

    _audit_report(db, action="VIEW_FACILITY_OPERATIONS_REPORT", facility_id=facility_id, start_date=start_date, end_date=end_date, actor_user_id=actor_user_id)
    return {"facility_id": str(facility_id), "start_date": start_date, "end_date": end_date, "patients": patients, "encounters": encounters, "diagnoses": diagnoses, "prescriptions": prescriptions, "admissions": admissions, "referrals": referrals, "charges_total": charges_total, "invoices_total": invoices_total, "confirmed_payments": confirmed_payments, "stock_received_quantity": received, "stock_dispensed_quantity": dispensed, "top_diagnoses": top_diagnoses, "daily": [daily[d] for d in daily_dates]}
