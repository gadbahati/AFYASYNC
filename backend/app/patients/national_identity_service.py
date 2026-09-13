from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.patients.models import AfyaIdentity, PatientFacility, Person
from app.patients.national_identity_schemas import NationalIdentityResolution


def resolve_national_identity(
    db: Session,
    afya_id: str,
    *,
    actor_user_id: UUID,
) -> NationalIdentityResolution | None:
    normalized = afya_id.strip().upper()
    if not normalized:
        return None

    row = db.execute(
        select(Person, AfyaIdentity)
        .join(AfyaIdentity, AfyaIdentity.person_id == Person.id)
        .where(AfyaIdentity.afya_id == normalized)
    ).first()
    if row is None:
        record_audit(
            db,
            action="NATIONAL_IDENTITY_LOOKUP",
            resource_type="AFYA_ID",
            resource_id=normalized[:20],
            result="NOT_FOUND",
            user_id=actor_user_id,
            metadata={"matched": False},
            commit=True,
        )
        return None

    person, identity = row
    active_facility_count = int(
        db.scalar(
            select(func.count(PatientFacility.id)).where(
                PatientFacility.patient_id == person.id,
                PatientFacility.status == "ACTIVE",
            )
        )
        or 0
    )

    record_audit(
        db,
        action="NATIONAL_IDENTITY_LOOKUP",
        resource_type="PERSON",
        resource_id=str(person.id),
        result="SUCCESS",
        user_id=actor_user_id,
        patient_id=person.id,
        metadata={"afya_id": identity.afya_id, "active_facility_count": active_facility_count},
        commit=True,
    )
    return NationalIdentityResolution(
        afya_id=identity.afya_id,
        person_id=person.id,
        first_name=person.first_name,
        middle_name=person.middle_name,
        last_name=person.last_name,
        date_of_birth=person.date_of_birth,
        sex=person.sex,
        patient_status=person.status,
        active_facility_count=active_facility_count,
        identity_status=identity.status,
    )
