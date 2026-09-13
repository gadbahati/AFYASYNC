from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.benefits.models import BenefitPackage
from app.audit.service import record_audit
from app.coverage.models import Coverage, Payer
from app.encounters.models import Encounter
from app.patients.models import PatientFacility
from app.preauthorizations.eligibility import EligibilityError, check_coverage_eligibility
from app.preauthorizations.models import PreAuthorization


class PreAuthorizationError(ValueError):
    pass


def _coverage(db: Session, patient_id: UUID, coverage_id: UUID, payer_id: UUID) -> Coverage:
    coverage = db.scalar(select(Coverage).where(Coverage.id == coverage_id, Coverage.person_id == patient_id, Coverage.payer_id == payer_id))
    if coverage is None:
        raise PreAuthorizationError("COVERAGE_NOT_FOUND")
    if coverage.status != "ACTIVE" or coverage.verification_status != "VERIFIED":
        raise PreAuthorizationError("VERIFIED_COVERAGE_REQUIRED")
    today = date.today()
    if coverage.start_date and coverage.start_date > today:
        raise PreAuthorizationError("COVERAGE_NOT_ACTIVE")
    if coverage.end_date and coverage.end_date < today:
        raise PreAuthorizationError("COVERAGE_EXPIRED")
    payer = db.get(Payer, payer_id)
    if payer is None or payer.status != "ACTIVE":
        raise PreAuthorizationError("PAYER_NOT_ACTIVE")
    return coverage


def request_preauthorization(db: Session, *, facility_id: UUID, actor_user_id: UUID, payload, idempotency_key: str | None = None) -> PreAuthorization:
    if idempotency_key:
        existing = db.scalar(select(PreAuthorization).where(PreAuthorization.facility_id == facility_id, PreAuthorization.idempotency_key == idempotency_key))
        if existing is not None:
            return existing

    membership = db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id == payload.patient_id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE"))
    if membership is None:
        raise PreAuthorizationError("PATIENT_NOT_IN_FACILITY")

    coverage = _coverage(db, payload.patient_id, payload.coverage_id, payload.payer_id)
    service_code = payload.requested_services[0].strip().upper() if payload.requested_services else None
    service_type = payload.department.strip().upper()
    try:
        eligibility = check_coverage_eligibility(db, patient_id=payload.patient_id, coverage_id=coverage.id, service_code=service_code, service_type=service_type, actor_user_id=actor_user_id, facility_id=facility_id)
    except EligibilityError as exc:
        raise PreAuthorizationError(str(exc)) from exc
    if not eligibility.get("eligible"):
        raise PreAuthorizationError(str(eligibility.get("reason")))

    if payload.encounter_id is not None:
        encounter = db.scalar(select(Encounter).where(Encounter.id == payload.encounter_id, Encounter.patient_id == payload.patient_id, Encounter.facility_id == facility_id))
        if encounter is None:
            raise PreAuthorizationError("ENCOUNTER_NOT_FOUND")
        if encounter.status != "OPEN":
            raise PreAuthorizationError("ENCOUNTER_NOT_OPEN")

    payer = db.get(Payer, payload.payer_id)
    package_code = payload.benefit_package_code.strip().upper()
    package = db.scalar(select(BenefitPackage).where(BenefitPackage.package_code == package_code, BenefitPackage.payer_code == payer.code, BenefitPackage.status == "ACTIVE")) if payer else None
    if package is None:
        raise PreAuthorizationError("BENEFIT_PACKAGE_NOT_FOUND")

    requested_amount = Decimal(str(payload.requested_amount)).quantize(Decimal("0.01"))
    authorization = PreAuthorization(
        authorization_number=f"PA-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}",
        patient_id=payload.patient_id,
        facility_id=facility_id,
        encounter_id=payload.encounter_id,
        coverage_id=payload.coverage_id,
        payer_id=payload.payer_id,
        benefit_package_code=package.package_code,
        care_setting=payload.care_setting,
        department=service_type,
        requested_services=[item.strip().upper() for item in payload.requested_services],
        requested_amount=requested_amount,
        idempotency_key=idempotency_key,
        status="PENDING",
    )
    db.add(authorization)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if idempotency_key:
            existing = db.scalar(select(PreAuthorization).where(PreAuthorization.facility_id == facility_id, PreAuthorization.idempotency_key == idempotency_key))
            if existing is not None:
                return existing
        raise PreAuthorizationError("PREAUTHORIZATION_CREATE_FAILED") from exc
    record_audit(db, action="REQUEST_PREAUTHORIZATION", resource_type="PREAUTHORIZATION", resource_id=str(authorization.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=payload.patient_id, metadata={"authorization_number": authorization.authorization_number, "care_setting": payload.care_setting, "benefit_package_code": package.package_code, "payer_id": str(payload.payer_id), "benefit_rule_id": str(eligibility["benefit_rule_id"])}, commit=False)
    db.commit()
    db.refresh(authorization)
    return authorization


def decide_preauthorization(db: Session, *, authorization_id: UUID, facility_id: UUID, actor_user_id: UUID, decision) -> PreAuthorization:
    authorization = db.scalar(select(PreAuthorization).where(PreAuthorization.id == authorization_id).with_for_update())
    if authorization is None:
        raise PreAuthorizationError("PREAUTH_NOT_FOUND")
    if authorization.facility_id != facility_id:
        raise PreAuthorizationError("FACILITY_ACCESS_DENIED")
    if authorization.status not in {"PENDING", "AUTHORIZED_PENDING_VISIT"}:
        raise PreAuthorizationError("PREAUTH_NOT_DECIDABLE")
    approved_amount = Decimal(str(decision.approved_amount)).quantize(Decimal("0.01"))
    requested_amount = Decimal(str(authorization.requested_amount)).quantize(Decimal("0.01"))
    if approved_amount > requested_amount:
        raise PreAuthorizationError("APPROVED_AMOUNT_EXCEEDS_REQUEST")
    if decision.status == "REJECTED" and approved_amount != Decimal("0.00"):
        raise PreAuthorizationError("REJECTED_AMOUNT_MUST_BE_ZERO")
    if decision.status in {"AUTHORIZED", "AUTHORIZED_PENDING_VISIT"} and approved_amount == Decimal("0.00"):
        raise PreAuthorizationError("INVALID_APPROVED_AMOUNT")
    authorization.status = decision.status
    authorization.approved_amount = approved_amount
    authorization.external_reference = decision.external_reference.strip() if decision.external_reference else None
    authorization.decided_at = datetime.now(timezone.utc)
    db.flush()
    record_audit(db, action="DECIDE_PREAUTHORIZATION", resource_type="PREAUTHORIZATION", resource_id=str(authorization.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=authorization.patient_id, metadata={"authorization_number": authorization.authorization_number, "status": authorization.status, "approved_amount": str(authorization.approved_amount), "external_reference": authorization.external_reference}, commit=False)
    db.commit()
    db.refresh(authorization)
    return authorization
