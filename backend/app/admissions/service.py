from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.benefits.models import BenefitPackage
from app.coverage.models import Coverage, Payer
from app.encounters.service import create_encounter
from app.patients.models import AfyaIdentity, Person, PatientFacility
from app.admissions.models import Admission


def lookup_sha_member(db: Session, *, membership_number: str, facility_id: UUID) -> dict:
    coverage = db.scalar(
        select(Coverage)
        .join(Payer, Payer.id == Coverage.payer_id)
        .join(Person, Person.id == Coverage.person_id)
        .join(PatientFacility, PatientFacility.patient_id == Coverage.person_id)
        .where(
            Coverage.membership_number == membership_number,
            Coverage.status == "ACTIVE",
            Payer.code == "SHA",
            PatientFacility.facility_id == facility_id,
            PatientFacility.status == "ACTIVE",
        )
        .order_by(Coverage.created_at.desc())
    )
    if coverage is None:
        raise ValueError("SHA_MEMBER_NOT_FOUND")

    today = date.today()
    if coverage.start_date and coverage.start_date > today:
        raise ValueError("SHA_COVERAGE_NOT_ACTIVE")
    if coverage.end_date and coverage.end_date < today:
        raise ValueError("SHA_COVERAGE_EXPIRED")

    person = db.get(Person, coverage.person_id)
    identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == coverage.person_id))
    if person is None or identity is None:
        raise ValueError("PATIENT_NOT_FOUND")

    packages = list(
        db.scalars(
            select(BenefitPackage.package_code)
            .where(BenefitPackage.payer_code == "SHA", BenefitPackage.status == "ACTIVE")
            .order_by(BenefitPackage.package_code)
        )
    )
    return {
        "person_id": person.id,
        "afya_id": identity.afya_id,
        "membership_number": coverage.membership_number,
        "full_name": " ".join(part for part in [person.first_name, person.middle_name, person.last_name] if part),
        "date_of_birth": person.date_of_birth.isoformat() if person.date_of_birth else None,
        "sex": person.sex,
        "coverage_status": coverage.verification_status,
        "benefit_package_codes": packages,
    }


def start_admission(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    department_id: UUID,
    benefit_package_code: str,
    ward: str,
    bed: str,
    diagnosis: str | None,
    created_by: UUID,
    actor_user_id: UUID,
) -> Admission:
    membership = db.scalar(
        select(PatientFacility.id).where(
            PatientFacility.patient_id == patient_id,
            PatientFacility.facility_id == facility_id,
            PatientFacility.status == "ACTIVE",
        )
    )
    if membership is None:
        raise ValueError("PATIENT_NOT_IN_FACILITY")

    package = db.scalar(
        select(BenefitPackage).where(
            BenefitPackage.package_code == benefit_package_code,
            BenefitPackage.payer_code == "SHA",
            BenefitPackage.status == "ACTIVE",
        )
    )
    if package is None:
        raise ValueError("BENEFIT_PACKAGE_NOT_FOUND")

    existing = db.scalar(
        select(Admission.id).where(
            Admission.patient_id == patient_id,
            Admission.facility_id == facility_id,
            Admission.status == "ADMITTED",
        )
    )
    if existing is not None:
        raise ValueError("PATIENT_ALREADY_ADMITTED")

    encounter = create_encounter(
        db,
        {
            "patient_id": patient_id,
            "facility_id": facility_id,
            "department_id": department_id,
            "encounter_type": "INPATIENT",
            "reason": diagnosis,
        },
        created_by,
        actor_user_id=actor_user_id,
        commit=False,
    )

    admission = Admission(
        admission_number=f"ADM-{uuid4().hex[:12].upper()}",
        patient_id=patient_id,
        facility_id=facility_id,
        encounter_id=encounter.id,
        benefit_package_code=benefit_package_code,
        ward=ward,
        bed=bed,
        diagnosis=diagnosis,
    )
    db.add(admission)
    db.flush()
    record_audit(
        db,
        action="ADMISSION_STARTED",
        resource_type="ADMISSION",
        resource_id=str(admission.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=patient_id,
        metadata={"admission_number": admission.admission_number, "benefit_package_code": benefit_package_code, "ward": ward, "bed": bed},
        commit=False,
    )
    db.commit()
    db.refresh(admission)
    return admission
