from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.benefits.models import BenefitPackage
from app.coverage.models import Coverage, Payer
from app.encounters.models import Encounter
from app.patients.models import PatientFacility
from app.preauthorizations.models import PreAuthorization


class PreAuthorizationError(ValueError):
    pass


def _coverage(db: Session, patient_id: UUID, coverage_id: UUID, payer_id: UUID) -> Coverage:
    coverage = db.scalar(
        select(Coverage).where(
            Coverage.id == coverage_id,
            Coverage.person_id == patient_id,
            Coverage.payer_id == payer_id,
        )
    )
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
    if payer is None or payer.code != "SHA" or payer.status != "ACTIVE":
        raise PreAuthorizationError("SHA_PAYER_REQUIRED")
    return coverage


def request_preauthorization(db: Session, *, facility_id: UUID, actor_user_id: UUID, payload) -> PreAuthorization:
    membership = db.scalar(
        select(PatientFacility.id).where(
            PatientFacility.patient_id == payload.patient_id,
            PatientFacility.facility_id == facility_id,
            PatientFacility.status == "ACTIVE",
        )
    )
    if membership is None:
        raise PreAuthorizationError("PATIENT_NOT_IN_FACILITY")

    _coverage(db, payload.patient_id, payload.coverage_id, payload.payer_id)

    if payload.encounter_id is not None:
        encounter = db.scalar(
            select(Encounter).where(
                Encounter.id == payload.encounter_id,
                Encounter.patient_id == payload.patient_id,
                Encounter.facility_id == facility_id,
            )
        )
        if encounter is None:
            raise PreAuthorizationError("ENCOUNTER_NOT_FOUND")
        if encounter.status != "OPEN":
            raise PreAuthorizationError("ENCOUNTER_NOT_OPEN")

    package = db.scalar(
        select(BenefitPackage).where(
            BenefitPackage.package_code == payload.benefit_package_code,
            BenefitPackage.payer_code == "SHA",
            BenefitPackage.status == "ACTIVE",
        )
    )
    if package is None:
        raise PreAuthorizationError("BENEFIT_PACKAGE_NOT_FOUND")
    if payload.care_setting == "INPATIENT" and payload.benefit_package_code not in {"SHA-07", "SHA-08"}:
        raise PreAuthorizationError("INPATIENT_SHA_PACKAGE_REQUIRED")

    authorization = PreAuthorization(
        authorization_number=f"PA-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}",
        patient_id=payload.patient_id,
        facility_id=facility_id,
        encounter_id=payload.encounter_id,
        coverage_id=payload.coverage_id,
        payer_id=payload.payer_id,
        benefit_package_code=payload.benefit_package_code,
        care_setting=payload.care_setting,
        department=payload.department,
        requested_services=payload.requested_services,
        requested_amount=payload.requested_amount,
        status="PENDING",
    )
    db.add(authorization)
    db.flush()
    record_audit(
        db,
        action="REQUEST_PREAUTHORIZATION",
        resource_type="PREAUTHORIZATION",
        resource_id=str(authorization.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=payload.patient_id,
        metadata={
            "authorization_number": authorization.authorization_number,
            "care_setting": payload.care_setting,
            "benefit_package_code": payload.benefit_package_code,
        },
        commit=False,
    )
    db.commit()
    db.refresh(authorization)
    return authorization


def decide_preauthorization(
    db: Session,
    *,
    authorization_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID,
    decision,
) -> PreAuthorization:
    authorization = db.scalar(
        select(PreAuthorization).where(PreAuthorization.id == authorization_id).with_for_update()
    )
    if authorization is None:
        raise PreAuthorizationError("PREAUTH_NOT_FOUND")
    if authorization.facility_id != facility_id:
        raise PreAuthorizationError("FACILITY_ACCESS_DENIED")
    if authorization.status not in {"PENDING", "AUTHORIZED_PENDING_VISIT"}:
        raise PreAuthorizationError("PREAUTH_NOT_DECIDABLE")
    if decision.approved_amount > float(authorization.requested_amount):
        raise PreAuthorizationError("APPROVED_AMOUNT_EXCEEDS_REQUEST")
    if decision.status == "REJECTED" and decision.approved_amount != 0:
        raise PreAuthorizationError("REJECTED_AMOUNT_MUST_BE_ZERO")

    authorization.status = decision.status
    authorization.approved_amount = decision.approved_amount
    authorization.external_reference = decision.external_reference
    authorization.decided_at = datetime.now(timezone.utc)
    db.flush()
    record_audit(
        db,
        action="DECIDE_PREAUTHORIZATION",
        resource_type="PREAUTHORIZATION",
        resource_id=str(authorization.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=authorization.patient_id,
        metadata={
            "authorization_number": authorization.authorization_number,
            "status": authorization.status,
            "approved_amount": str(authorization.approved_amount),
            "external_reference": authorization.external_reference,
        },
        commit=False,
    )
    db.commit()
    db.refresh(authorization)
    return authorization
