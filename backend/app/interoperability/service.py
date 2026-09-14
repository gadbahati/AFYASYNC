from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.patients.models import AfyaIdentity, PatientFacility, Person
from app.interoperability.schemas import FHIRPatientResource


def get_fhir_patient(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID,
) -> FHIRPatientResource:
    enrolled = db.scalar(select(PatientFacility.id).where(
        PatientFacility.patient_id == patient_id,
        PatientFacility.facility_id == facility_id,
        PatientFacility.status == "ACTIVE",
    ))
    if enrolled is None:
        raise ValueError("PATIENT_NOT_IN_FACILITY")

    person = db.get(Person, patient_id)
    if person is None or person.status != "ACTIVE":
        raise ValueError("PATIENT_NOT_FOUND")

    identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == patient_id))
    if identity is None or identity.status != "ACTIVE":
        raise ValueError("IDENTITY_NOT_ACTIVE")

    record_audit(
        db,
        action="INTEROPERABILITY_PATIENT_READ",
        resource_type="PERSON",
        resource_id=str(patient_id),
        result="SUCCESS",
        user_id=actor_user_id,
        patient_id=patient_id,
        metadata={"facility_id": str(facility_id), "format": "FHIR_PATIENT_MINIMAL"},
        commit=True,
    )

    return FHIRPatientResource(
        id=person.id,
        identifier=[{"system": "AfyaSync", "value": identity.afya_id}],
        name=[{"use": "official", "family": person.last_name, "given": [x for x in [person.first_name, person.middle_name] if x]}],
        birthDate=person.date_of_birth,
        gender=person.sex,
        active=person.status == "ACTIVE",
    )
