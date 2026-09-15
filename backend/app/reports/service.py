from datetime import date, datetime, time, timezone
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
from app.pharmacy.models import MedicationAction, Prescription, StockMovement
from app.clinical.models import Diagnosis
from app.referrals.models import Referral


def _window(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    if end_date < start_date:
        raise ValueError("INVALID_REPORT_DATE_RANGE")
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
    return start, end


def _money(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def build_facility_report(db: Session, facility_id: UUID, start_date: date, end_date: date, *, actor_user_id: UUID | None = None) -> dict[str, object]:
    start, end = _window(start_date, end_date)
    patients = int(db.scalar(select(func.count(PatientFacility.id)).where(PatientFacility.facility_id == facility_id, PatientFacility.created_at >= start, PatientFacility.created_at <= end)) or 0)
    encounters = int(db.scalar(select(func.count(Encounter.id)).where(Encounter.facility_id == facility_id, Encounter.created_at >= start, Encounter.created_at <= end)) or 0)
    charges_total = _money(db.scalar(select(func.coalesce(func.sum(Charge.total_amount), 0)).where(Charge.facility_id == facility_id, Charge.created_at >= start, Charge.created_at <= end, Charge.status == "ACTIVE")))
    invoice_totals = db.execute(select(func.coalesce(func.sum(Invoice.total_amount), 0), func.coalesce(func.sum(Invoice.payer_amount), 0), func.coalesce(func.sum(Invoice.patient_amount), 0)).where(Invoice.facility_id == facility_id, Invoice.created_at >= start, Invoice.created_at <= end, Invoice.status != "VOID")).one()
    invoices_total, payer_billed, patient_billed = (_money(invoice_totals[0]), _money(invoice_totals[1]), _money(invoice_totals[2]))
    confirmed_payments = _money(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.facility_id == facility_id, Payment.created_at >= start, Payment.created_at <= end, Payment.status == "CONFIRMED")))
    claim_filter = (Claim.updated_at >= start, Claim.updated_at <= end, Invoice.facility_id == facility_id)
    claim_totals = db.execute(select(func.count(Claim.id), func.coalesce(func.sum(Claim.claim_amount), 0), func.coalesce(func.sum(Claim.approved_amount), 0), func.coalesce(func.sum(Claim.paid_amount), 0)).join(Invoice, Invoice.id == Claim.invoice_id).where(*claim_filter)).one()
    claims, claims_amount, claims_approved, claims_paid = int(claim_totals[0] or 0), _money(claim_totals[1]), _money(claim_totals[2]), _money(claim_totals[3])
    status_rows = db.execute(select(Claim.status, func.count(Claim.id), func.coalesce(func.sum(Claim.claim_amount), 0), func.coalesce(func.sum(Claim.approved_amount), 0), func.coalesce(func.sum(Claim.paid_amount), 0)).join(Invoice, Invoice.id == Claim.invoice_id).where(*claim_filter).group_by(Claim.status).order_by(Claim.status)).all()
    claim_statuses = [{"status": row[0], "count": int(row[1] or 0), "amount": _money(row[2]), "approved_amount": _money(row[3]), "paid_amount": _money(row[4])} for row in status_rows]
    payer_rows = db.execute(select(Payer.id, Payer.name, Payer.code, func.count(Claim.id), func.coalesce(func.sum(Claim.claim_amount), 0), func.coalesce(func.sum(Claim.approved_amount), 0), func.coalesce(func.sum(Claim.paid_amount), 0)).join(Invoice, Invoice.id == Claim.invoice_id).join(Payer, Payer.id == Claim.payer_id).where(*claim_filter).group_by(Payer.id, Payer.name, Payer.code).order_by(func.sum(Claim.claim_amount).desc(), Payer.name)).all()
    payer_claims = []
    for row in payer_rows:
        approved, paid = _money(row[5]), _money(row[6])
        payer_claims.append({"payer_id": str(row[0]), "payer_name": row[1], "payer_code": row[2], "claims": int(row[3] or 0), "amount": _money(row[4]), "approved_amount": approved, "paid_amount": paid, "receivable": max(approved - paid, Decimal("0.00"))})
    record_audit(db, action="VIEW_FACILITY_REPORT", resource_type="FACILITY_REPORT", resource_id=str(facility_id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, metadata={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}, commit=True)
    return {"facility_id": str(facility_id), "start_date": start_date, "end_date": end_date, "patients": patients, "encounters": encounters, "charges_total": charges_total, "invoices_total": invoices_total, "payer_billed": payer_billed, "patient_billed": patient_billed, "confirmed_payments": confirmed_payments, "claims": claims, "claims_amount": claims_amount, "claims_approved": claims_approved, "claims_paid": claims_paid, "claims_receivable": max(claims_approved - claims_paid, Decimal("0.00")), "claim_statuses": claim_statuses, "payer_claims": payer_claims}


def build_facility_operations_report(db: Session, facility_id: UUID, start_date: date, end_date: date, *, actor_user_id: UUID | None = None) -> dict[str, object]:
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
    received = Decimal("0.00")
    dispensed = Decimal("0.00")
    movement_rows = db.execute(select(StockMovement.movement_type, func.coalesce(func.sum(StockMovement.quantity), 0)).join(StockMovement.inventory_item_id == StockMovement.inventory_item_id).where(StockMovement.created_at >= start, StockMovement.created_at <= end)).all()
    # Facility isolation for stock movements is applied through InventoryItem in the dedicated query below.
    from app.pharmacy.models import InventoryItem
    movement_rows = db.execute(select(StockMovement.movement_type, func.coalesce(func.sum(StockMovement.quantity), 0)).join(InventoryItem, InventoryItem.id == StockMovement.inventory_item_id).where(InventoryItem.facility_id == facility_id, StockMovement.created_at >= start, StockMovement.created_at <= end).group_by(StockMovement.movement_type)).all()
    for movement_type, quantity in movement_rows:
        if movement_type == "RECEIVE": received += Decimal(str(quantity or 0))
        if movement_type in {"DISPENSE", "ISSUE"}: dispensed += Decimal(str(quantity or 0))
    diagnosis_rows = db.execute(select(Diagnosis.diagnosis_name, func.count(Diagnosis.id)).join(Encounter, Encounter.id == Diagnosis.encounter_id).where(*enc_filter).group_by(Diagnosis.diagnosis_name).order_by(func.count(Diagnosis.id).desc(), Diagnosis.diagnosis_name).limit(20)).all()
    top_diagnoses = [{"diagnosis": row[0], "count": int(row[1] or 0)} for row in diagnosis_rows]
    daily = []
    current = start_date
    while current <= end_date:
        day_start, day_end = _window(current, current)
        day_enc_filter = (Encounter.facility_id == facility_id, Encounter.created_at >= day_start, Encounter.created_at <= day_end)
        day_patients = int(db.scalar(select(func.count(PatientFacility.id)).where(PatientFacility.facility_id == facility_id, PatientFacility.created_at >= day_start, PatientFacility.created_at <= day_end)) or 0)
        day_encounters = int(db.scalar(select(func.count(Encounter.id)).where(*day_enc_filter)) or 0)
        day_diagnoses = int(db.scalar(select(func.count(Diagnosis.id)).join(Encounter, Encounter.id == Diagnosis.encounter_id).where(*day_enc_filter)) or 0)
        day_rx = int(db.scalar(select(func.count(Prescription.id)).join(Encounter, Encounter.id == Prescription.encounter_id).where(*day_enc_filter)) or 0)
        day_adm = int(db.scalar(select(func.count(Admission.id)).where(Admission.facility_id == facility_id, Admission.created_at >= day_start, Admission.created_at <= day_end)) or 0)
        day_ref = int(db.scalar(select(func.count(Referral.id)).where(Referral.source_facility_id == facility_id, Referral.created_at >= day_start, Referral.created_at <= day_end)) or 0)
        day_charges = _money(db.scalar(select(func.coalesce(func.sum(Charge.total_amount), 0)).where(Charge.facility_id == facility_id, Charge.created_at >= day_start, Charge.created_at <= day_end, Charge.status == "ACTIVE")))
        day_invoices = _money(db.scalar(select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(Invoice.facility_id == facility_id, Invoice.created_at >= day_start, Invoice.created_at <= day_end, Invoice.status != "VOID")))
        day_payments = _money(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.facility_id == facility_id, Payment.created_at >= day_start, Payment.created_at <= day_end, Payment.status == "CONFIRMED")))
        day_movements = db.execute(select(StockMovement.movement_type, func.coalesce(func.sum(StockMovement.quantity), 0)).join(InventoryItem, InventoryItem.id == StockMovement.inventory_item_id).where(InventoryItem.facility_id == facility_id, StockMovement.created_at >= day_start, StockMovement.created_at <= day_end).group_by(StockMovement.movement_type)).all()
        day_received = sum(Decimal(str(q or 0)) for t, q in day_movements if t == "RECEIVE")
        day_dispensed = sum(Decimal(str(q or 0)) for t, q in day_movements if t in {"DISPENSE", "ISSUE"})
        daily.append({"date": current, "patients": day_patients, "encounters": day_encounters, "diagnoses": day_diagnoses, "prescriptions": day_rx, "admissions": day_adm, "referrals": day_ref, "charges": day_charges, "invoices": day_invoices, "payments": day_payments, "stock_received_quantity": day_received, "stock_dispensed_quantity": day_dispensed})
        current = current.fromordinal(current.toordinal() + 1)
    record_audit(db, action="VIEW_FACILITY_OPERATIONS_REPORT", resource_type="FACILITY_OPERATIONS_REPORT", resource_id=str(facility_id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, metadata={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}, commit=True)
    return {"facility_id": str(facility_id), "start_date": start_date, "end_date": end_date, "patients": patients, "encounters": encounters, "diagnoses": diagnoses, "prescriptions": prescriptions, "admissions": admissions, "referrals": referrals, "charges_total": charges_total, "invoices_total": invoices_total, "confirmed_payments": confirmed_payments, "stock_received_quantity": received, "stock_dispensed_quantity": dispensed, "top_diagnoses": top_diagnoses, "daily": daily}
