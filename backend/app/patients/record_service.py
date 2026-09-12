from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from app.admissions.models import Admission
from app.appointments.models import Appointment, Queue, QueueEntry
from app.billing.models import Charge, Invoice, InvoiceItem, Payment, Service
from app.claims.models import Claim, ClaimItem, ClaimResponse, Reconciliation
from app.clinical.models import Consultation, Diagnosis, Vital
from app.coverage.models import Coverage, Payer, PayerPlan
from app.encounters.models import Encounter
from app.facilities.models import Department, Facility
from app.laboratory.models import LabOrder, LabOrderItem, LabResult, LabTest
from app.patients.models import AfyaIdentity, PatientFacility, Person
from app.pharmacy.models import Medication, MedicationAction, Prescription, PrescriptionItem
from app.preauthorizations.models import PreAuthorization
from app.referrals.models import Referral, Transfer


def get_patient_record_summary(db: Session, patient_id: UUID, facility_id: UUID) -> dict | None:
    """Return a complete, facility-scoped longitudinal patient record."""
    patient_row = db.execute(
        select(Person, PatientFacility)
        .join(PatientFacility, PatientFacility.patient_id == Person.id)
        .where(Person.id == patient_id, PatientFacility.facility_id == facility_id)
    ).first()
    if patient_row is None:
        return None
    patient, enrollment = patient_row
    afya_identity = db.execute(select(AfyaIdentity).where(AfyaIdentity.person_id == patient_id)).scalar_one()

    departments = {row.id: row.name for row in db.execute(select(Department).where(Department.facility_id == facility_id)).scalars()}
    encounters = list(db.execute(select(Encounter).where(Encounter.patient_id == patient_id, Encounter.facility_id == facility_id).order_by(Encounter.started_at.desc())).scalars())
    encounter_ids = [e.id for e in encounters]

    consultations = {}
    vitals = {}
    diagnoses = {}
    if encounter_ids:
        consultations = {x.encounter_id: x for x in db.execute(select(Consultation).where(Consultation.encounter_id.in_(encounter_ids))).scalars()}
        for x in db.execute(select(Vital).where(Vital.encounter_id.in_(encounter_ids)).order_by(Vital.recorded_at.desc())).scalars():
            vitals.setdefault(x.encounter_id, []).append(x)
        for x in db.execute(select(Diagnosis).where(Diagnosis.encounter_id.in_(encounter_ids)).order_by(Diagnosis.created_at.desc())).scalars():
            diagnoses.setdefault(x.encounter_id, []).append(x)

    lab_orders = list(db.execute(select(LabOrder).join(Encounter, Encounter.id == LabOrder.encounter_id).where(LabOrder.patient_id == patient_id, Encounter.facility_id == facility_id).order_by(LabOrder.created_at.desc())).scalars())
    lab_order_ids = [x.id for x in lab_orders]
    lab_items = list(db.execute(select(LabOrderItem, LabTest).join(LabTest, LabTest.id == LabOrderItem.test_id).where(LabOrderItem.lab_order_id.in_(lab_order_ids))).all()) if lab_order_ids else []
    lab_item_ids = [item.id for item, _ in lab_items]
    lab_results = {x.lab_order_item_id: x for x in db.execute(select(LabResult).where(LabResult.lab_order_item_id.in_(lab_item_ids))).scalars()} if lab_item_ids else {}

    prescriptions = list(db.execute(select(Prescription).join(Encounter, Encounter.id == Prescription.encounter_id).where(Prescription.patient_id == patient_id, Encounter.facility_id == facility_id).order_by(Prescription.created_at.desc())).scalars())
    prescription_ids = [x.id for x in prescriptions]
    prescription_items = list(db.execute(select(PrescriptionItem, Medication).join(Medication, Medication.id == PrescriptionItem.medication_id).where(PrescriptionItem.prescription_id.in_(prescription_ids))).all()) if prescription_ids else []
    medication_actions = list(db.execute(select(MedicationAction, Medication).join(Medication, Medication.id == MedicationAction.medication_id).where(MedicationAction.encounter_id.in_(encounter_ids)).order_by(MedicationAction.performed_at.desc())).all()) if encounter_ids else []

    charges = list(db.execute(select(Charge, Service).join(Service, Service.id == Charge.service_id).where(Charge.patient_id == patient_id, Charge.facility_id == facility_id).order_by(Charge.created_at.desc())).all())
    invoices = list(db.execute(select(Invoice).where(Invoice.patient_id == patient_id, Invoice.facility_id == facility_id).order_by(Invoice.created_at.desc())).scalars())
    invoice_ids = [x.id for x in invoices]
    invoice_items = list(db.execute(select(InvoiceItem).where(InvoiceItem.invoice_id.in_(invoice_ids))).scalars()) if invoice_ids else []
    payments = list(db.execute(select(Payment).where(Payment.patient_id == patient_id, Payment.facility_id == facility_id).order_by(Payment.created_at.desc())).scalars())

    claims = list(db.execute(select(Claim, Payer).join(Payer, Payer.id == Claim.payer_id).join(Invoice, Invoice.id == Claim.invoice_id).where(Claim.patient_id == patient_id, Invoice.facility_id == facility_id).order_by(Claim.updated_at.desc())).all())
    claim_ids = [x.id for x, _ in claims]
    claim_items = list(db.execute(select(ClaimItem).where(ClaimItem.claim_id.in_(claim_ids))).scalars()) if claim_ids else []
    claim_responses = list(db.execute(select(ClaimResponse).where(ClaimResponse.claim_id.in_(claim_ids)).order_by(ClaimResponse.received_at.desc())).scalars()) if claim_ids else []
    reconciliations = list(db.execute(select(Reconciliation).where(Reconciliation.claim_id.in_(claim_ids))).scalars()) if claim_ids else []

    coverages = list(db.execute(select(Coverage, Payer, PayerPlan).join(Payer, Payer.id == Coverage.payer_id).outerjoin(PayerPlan, PayerPlan.id == Coverage.payer_plan_id).where(Coverage.person_id == patient_id).order_by(Coverage.created_at.desc())).all())
    admissions = list(db.execute(select(Admission).join(Encounter, Encounter.id == Admission.encounter_id).where(Admission.patient_id == patient_id, Admission.facility_id == facility_id, Encounter.facility_id == facility_id).order_by(Admission.admitted_at.desc())).scalars())
    preauthorizations = list(db.execute(select(PreAuthorization, Payer).join(Payer, Payer.id == PreAuthorization.payer_id).where(PreAuthorization.patient_id == patient_id, PreAuthorization.facility_id == facility_id).order_by(PreAuthorization.requested_at.desc())).all())
    appointments = list(db.execute(select(Appointment).where(Appointment.patient_id == patient_id, Appointment.facility_id == facility_id).order_by(Appointment.appointment_at.desc())).scalars())
    queue_entries = list(db.execute(select(QueueEntry, Queue).join(Queue, Queue.id == QueueEntry.queue_id).where(QueueEntry.patient_id == patient_id, Queue.facility_id == facility_id).order_by(QueueEntry.queued_at.desc())).all())

    source_facility = aliased(Facility)
    destination_facility = aliased(Facility)
    referrals = list(db.execute(select(Referral, source_facility, destination_facility).join(source_facility, source_facility.id == Referral.source_facility_id).join(destination_facility, destination_facility.id == Referral.destination_facility_id).where(Referral.patient_id == patient_id, or_(Referral.source_facility_id == facility_id, Referral.destination_facility_id == facility_id)).order_by(Referral.created_at.desc())).all())
    transfers = list(db.execute(select(Transfer, source_facility, destination_facility).join(source_facility, source_facility.id == Transfer.source_facility_id).join(destination_facility, destination_facility.id == Transfer.destination_facility_id).where(Transfer.patient_id == patient_id, or_(Transfer.source_facility_id == facility_id, Transfer.destination_facility_id == facility_id)).order_by(Transfer.created_at.desc())).all())

    return {
        "patient": {"id": str(patient.id), "afya_id": afya_identity.afya_id, "first_name": patient.first_name, "middle_name": patient.middle_name, "last_name": patient.last_name, "date_of_birth": patient.date_of_birth, "sex": patient.sex, "phone": patient.phone, "email": patient.email, "address": patient.address, "emergency_contact_name": patient.emergency_contact_name, "emergency_contact_phone": patient.emergency_contact_phone, "next_of_kin_name": patient.next_of_kin_name, "next_of_kin_phone": patient.next_of_kin_phone, "status": patient.status, "enrollment_status": enrollment.status, "registered_at": patient.created_at},
        "coverage": [{"id": str(c.id), "payer_id": str(p.id), "payer_name": p.name, "payer_code": p.code, "plan_id": str(plan.id) if plan else None, "plan_name": plan.name if plan else None, "membership_number": c.membership_number, "start_date": c.start_date, "end_date": c.end_date, "verification_status": c.verification_status, "status": c.status} for c, p, plan in coverages],
        "encounters": [{"id": str(e.id), "encounter_id": e.encounter_id, "patient_id": str(e.patient_id), "facility_id": str(e.facility_id), "department_id": str(e.department_id), "department_name": departments.get(e.department_id), "encounter_type": e.encounter_type, "type": e.encounter_type, "reason": e.reason, "status": e.status, "started_at": e.started_at, "ended_at": e.ended_at, "created_by": str(e.created_by), "consultation": ({"id": str(c.id), "encounter_id": str(c.encounter_id), "doctor_id": str(c.doctor_id), "chief_complaint": c.chief_complaint, "history": c.history, "examination": c.examination, "assessment": c.assessment, "clinical_notes": c.clinical_notes, "treatment_plan": c.treatment_plan, "created_at": c.created_at, "updated_at": c.updated_at} if (c := consultations.get(e.id)) else None), "vitals": [{"id": str(v.id), "encounter_id": str(v.encounter_id), "recorded_by": str(v.recorded_by), "systolic_bp": v.systolic_bp, "diastolic_bp": v.diastolic_bp, "pulse": v.pulse, "temperature_c": v.temperature_c, "respiratory_rate": v.respiratory_rate, "oxygen_saturation": v.oxygen_saturation, "weight_kg": v.weight_kg, "height_cm": v.height_cm, "bmi": v.bmi, "recorded_at": v.recorded_at} for v in vitals.get(e.id, [])], "diagnoses": [{"id": str(d.id), "encounter_id": str(d.encounter_id), "diagnosis_code": d.diagnosis_code, "diagnosis_name": d.diagnosis_name, "diagnosis_type": d.diagnosis_type, "status": d.status, "recorded_by": str(d.recorded_by), "created_at": d.created_at} for d in diagnoses.get(e.id, [])]} for e in encounters],
        "laboratory": [{"id": str(o.id), "order_id": o.order_id, "encounter_id": str(o.encounter_id), "priority": o.priority, "status": o.status, "forwarded_at": o.forwarded_at, "created_at": o.created_at, "items": [{"id": str(item.id), "test_id": str(test.id), "code": test.code, "name": test.name, "description": test.description, "category": test.category, "sample_type": test.sample_type, "price": test.price, "status": item.status, "charge_id": str(item.charge_id) if item.charge_id else None, "result": ({"id": str(r.id), "result": r.result, "unit": r.unit, "reference_range": r.reference_range, "comments": r.comments, "status": r.status, "created_at": r.created_at, "verified_at": r.verified_at, "verified_by": str(r.verified_by) if r.verified_by else None} if (r := lab_results.get(item.id)) else None)} for item, test in lab_items if item.lab_order_id == o.id]} for o in lab_orders],
        "prescriptions": [{"id": str(p.id), "prescription_id": p.prescription_id, "encounter_id": str(p.encounter_id), "patient_id": str(p.patient_id), "status": p.status, "created_at": p.created_at, "items": [{"id": str(item.id), "medication_id": str(m.id), "code": m.code, "name": m.name, "generic_name": m.generic_name, "strength": m.strength, "form": m.form, "dose": item.dose, "frequency": item.frequency, "duration": item.duration, "route": item.route, "quantity": item.quantity, "instructions": item.instructions} for item, m in prescription_items if item.prescription_id == p.id]} for p in prescriptions],
        "medication_actions": [{"id": str(a.id), "encounter_id": str(a.encounter_id), "prescription_item_id": str(a.prescription_item_id) if a.prescription_item_id else None, "medication_id": str(m.id), "medication_name": m.name, "action_type": a.action_type, "quantity": a.quantity, "performed_by": str(a.performed_by), "performed_at": a.performed_at, "notes": a.notes} for a, m in medication_actions],
        "admissions": [{"id": str(a.id), "admission_number": a.admission_number, "encounter_id": str(a.encounter_id), "benefit_package_code": a.benefit_package_code, "ward": a.ward, "bed": a.bed, "diagnosis": a.diagnosis, "status": a.status, "admitted_at": a.admitted_at, "discharged_at": a.discharged_at} for a in admissions],
        "preauthorizations": [{"id": str(a.id), "authorization_number": a.authorization_number, "encounter_id": str(a.encounter_id) if a.encounter_id else None, "payer_name": p.name, "benefit_package_code": a.benefit_package_code, "care_setting": a.care_setting, "department": a.department, "requested_services": a.requested_services, "status": a.status, "requested_amount": a.requested_amount, "approved_amount": a.approved_amount, "external_reference": a.external_reference, "requested_at": a.requested_at, "decided_at": a.decided_at} for a, p in preauthorizations],
        "billing": {"charges": [{"id": str(c.id), "charge_id": c.charge_id, "encounter_id": str(c.encounter_id), "service_code": s.code, "service_name": s.name, "service_type": s.service_type, "quantity": c.quantity, "unit_price": c.unit_price, "total_amount": c.total_amount, "source_type": c.source_type, "status": c.status, "created_at": c.created_at} for c, s in charges], "invoices": [{"id": str(i.id), "invoice_id": i.invoice_id, "encounter_id": str(i.encounter_id), "subtotal": i.subtotal, "payer_amount": i.payer_amount, "patient_amount": i.patient_amount, "total_amount": i.total_amount, "status": i.status, "created_at": i.created_at, "items": [{"id": str(ii.id), "description": ii.description, "quantity": ii.quantity, "unit_price": ii.unit_price, "amount": ii.amount, "payer_amount": ii.payer_amount, "patient_amount": ii.patient_amount} for ii in invoice_items if ii.invoice_id == i.id]} for i in invoices], "payments": [{"id": str(p.id), "transaction_id": p.transaction_id, "invoice_id": str(p.invoice_id), "amount": p.amount, "payment_method": p.payment_method, "provider": p.provider, "external_reference": p.external_reference, "status": p.status, "created_at": p.created_at, "confirmed_at": p.confirmed_at} for p in payments]},
        "claims": [{"id": str(c.id), "claim_id": c.claim_id, "invoice_id": str(c.invoice_id), "encounter_id": str(c.encounter_id), "payer_name": p.name, "claim_amount": c.claim_amount, "approved_amount": c.approved_amount, "paid_amount": c.paid_amount, "status": c.status, "submitted_at": c.submitted_at, "items": [{"id": str(i.id), "charge_id": str(i.charge_id), "service_code": i.service_code, "quantity": i.quantity, "amount": i.amount} for i in claim_items if i.claim_id == c.id], "responses": [{"id": str(r.id), "external_reference": r.external_reference, "status": r.status, "response_code": r.response_code, "response_message": r.response_message, "received_at": r.received_at} for r in claim_responses if r.claim_id == c.id], "reconciliation": next(({"id": str(r.id), "expected_amount": r.expected_amount, "received_amount": r.received_amount, "difference": r.difference, "status": r.status, "reconciled_by": str(r.reconciled_by) if r.reconciled_by else None, "reconciled_at": r.reconciled_at} for r in reconciliations if r.claim_id == c.id), None)} for c, p in claims],
        "appointments": [{"id": str(a.id), "patient_id": str(a.patient_id), "facility_id": str(a.facility_id), "department_id": str(a.department_id), "provider_id": str(a.provider_id) if a.provider_id else None, "appointment_at": a.appointment_at, "reason": a.reason, "status": a.status} for a in appointments],
        "queue_history": [{"id": str(q.id), "queue_name": queue.name, "department_id": str(queue.department_id), "appointment_id": str(q.appointment_id) if q.appointment_id else None, "encounter_id": str(q.encounter_id) if q.encounter_id else None, "priority": q.priority, "status": q.status, "queued_at": q.queued_at, "called_at": q.called_at, "completed_at": q.completed_at} for q, queue in queue_entries],
        "referrals": [{"id": str(r.id), "referral_id": r.referral_id, "patient_id": str(r.patient_id), "encounter_id": str(r.encounter_id), "source_facility_id": str(r.source_facility_id), "source_facility_name": sf.name, "destination_facility_id": str(r.destination_facility_id), "destination_facility_name": df.name, "destination_department_id": str(r.destination_department_id) if r.destination_department_id else None, "referred_by": str(r.referred_by), "reason": r.reason, "priority": r.priority, "clinical_summary": r.clinical_summary, "status": r.status, "created_at": r.created_at, "updated_at": r.updated_at} for r, sf, df in referrals],
        "transfers": [{"id": str(t.id), "transfer_id": t.transfer_id, "patient_id": str(t.patient_id), "referral_id": str(t.referral_id) if t.referral_id else None, "encounter_id": str(t.encounter_id), "source_facility_id": str(t.source_facility_id), "source_facility_name": sf.name, "destination_facility_id": str(t.destination_facility_id), "destination_facility_name": df.name, "requested_by": str(t.requested_by), "reason": t.reason, "status": t.status, "notes": t.notes, "created_at": t.created_at, "updated_at": t.updated_at} for t, sf, df in transfers],
    }
