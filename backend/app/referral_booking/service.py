from datetime import timezone
from uuid import UUID, uuid4
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.appointments.capacity_service import assert_capacity_for_slot, assert_patient_not_double_booked
from app.appointments.models import Appointment
from app.audit.service import record_audit
from app.care_coordination.models import CareCoordinationCase
from app.encounters.models import Encounter
from app.facilities.models import Department, Facility
from app.patients.models import Person
from app.provider_network.models import ProviderNetworkMembership, ProviderNetworkService
from app.rbac.models import Staff, User
from app.referrals.models import Referral
from .models import ReferralBooking

class BookingError(ValueError): pass

def _staff(db: Session, user_id: UUID, facility_id: UUID) -> UUID:
    user = db.get(User, user_id)
    if user is None or user.person_id is None: raise BookingError("STAFF_CONTEXT_REQUIRED")
    staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == facility_id, Staff.status == "ACTIVE").limit(1))
    if staff is None: raise BookingError("FACILITY_ACCESS_DENIED")
    return staff.id

def book(db: Session, *, source_facility_id: UUID, actor_user_id: UUID, payload: dict, idempotency_key: str) -> ReferralBooking:
    key = idempotency_key.strip()
    if not key or len(key) > 200: raise BookingError("INVALID_IDEMPOTENCY_KEY")
    existing = db.scalar(select(ReferralBooking).where(ReferralBooking.idempotency_key == key))
    if existing: return existing
    encounter = db.get(Encounter, payload["encounter_id"])
    if encounter is None or encounter.facility_id != source_facility_id or encounter.patient_id != payload["patient_id"] or encounter.status != "OPEN": raise BookingError("INVALID_SOURCE_ENCOUNTER")
    patient = db.get(Person, payload["patient_id"])
    if patient is None or patient.status != "ACTIVE": raise BookingError("PATIENT_NOT_FOUND")
    destination = db.get(Facility, payload["destination_facility_id"])
    if destination is None or destination.status != "ACTIVE" or destination.id == source_facility_id: raise BookingError("INVALID_DESTINATION_FACILITY")
    department = db.get(Department, payload["destination_department_id"])
    if department is None or department.facility_id != destination.id or department.status != "ACTIVE": raise BookingError("INVALID_DESTINATION_DEPARTMENT")
    membership = db.scalar(select(ProviderNetworkMembership).where(ProviderNetworkMembership.facility_id == destination.id, ProviderNetworkMembership.network_code == payload["network_code"], ProviderNetworkMembership.participation_status == "ACTIVE").limit(1))
    if membership is None or not membership.referral_enabled: raise BookingError("NETWORK_REFERRAL_NOT_ENABLED")
    service = db.scalar(select(ProviderNetworkService).where(ProviderNetworkService.facility_id == destination.id, ProviderNetworkService.network_code == payload["network_code"], ProviderNetworkService.service_code == payload["service_code"], ProviderNetworkService.status == "ACTIVE").limit(1))
    if service is None: raise BookingError("SERVICE_NOT_AVAILABLE")
    if service.department_code and service.department_code != department.code: raise BookingError("SERVICE_DEPARTMENT_MISMATCH")
    appointment_at = payload["appointment_at"]
    if appointment_at.tzinfo is None: appointment_at = appointment_at.replace(tzinfo=timezone.utc)
    appointment_at = appointment_at.astimezone(timezone.utc)
    lock_key = f"referral-booking:{destination.id}:{department.id}:{appointment_at.date().isoformat()}"
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": lock_key})
    assert_capacity_for_slot(db, facility_id=destination.id, department_id=department.id, appointment_at=appointment_at)
    assert_patient_not_double_booked(db, patient_id=patient.id, facility_id=destination.id, department_id=department.id, appointment_at=appointment_at)
    staff_id = _staff(db, actor_user_id, source_facility_id)
    referral = Referral(referral_id=f"REF-{uuid4().hex[:20].upper()}", patient_id=patient.id, encounter_id=encounter.id, source_facility_id=source_facility_id, destination_facility_id=destination.id, destination_department_id=department.id, referred_by=staff_id, reason=payload["reason"], priority=payload.get("priority", "ROUTINE"), clinical_summary=payload.get("clinical_summary"), status="ACCEPTED")
    db.add(referral); db.flush()
    appointment = Appointment(patient_id=patient.id, facility_id=destination.id, department_id=department.id, appointment_at=appointment_at, reason=payload["reason"], status="SCHEDULED")
    db.add(appointment); db.flush()
    case = CareCoordinationCase(case_number=f"CARE-{uuid4().hex[:18].upper()}", referral_id=referral.id, patient_id=patient.id, source_facility_id=source_facility_id, destination_facility_id=destination.id, status="SCHEDULED", appointment_at=appointment_at, notes=payload.get("notes"), created_by=actor_user_id)
    db.add(case); db.flush()
    booking = ReferralBooking(booking_reference=f"RFB-{uuid4().hex[:20].upper()}", idempotency_key=key, patient_id=patient.id, source_facility_id=source_facility_id, destination_facility_id=destination.id, referral_id=referral.id, appointment_id=appointment.id, coordination_case_id=case.id, service_code=service.service_code, network_code=service.network_code, appointment_at=appointment_at, status="BOOKED", notes=payload.get("notes"), created_by=actor_user_id)
    db.add(booking); db.flush()
    record_audit(db, action="CREATE_REFERRAL_BOOKING", resource_type="REFERRAL_BOOKING", resource_id=str(booking.id), result="SUCCESS", user_id=actor_user_id, facility_id=source_facility_id, patient_id=patient.id, metadata={"booking_reference":booking.booking_reference,"referral_id":str(referral.id),"appointment_id":str(appointment.id),"destination_facility_id":str(destination.id),"service_code":service.service_code,"network_code":service.network_code}, commit=False)
    db.commit(); db.refresh(booking); return booking
