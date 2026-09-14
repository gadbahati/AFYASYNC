import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.patients.models import AfyaIdentity, Person
from app.patients.national_identity_schemas import NationalIdentityResolution


def _audit_identifier(value: str) -> str:
    """Return a deterministic non-reversible identifier for audit trails."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
            resource_id=_audit_identifier(normalized),
            result="NOT_FOUND",
            user_id=actor_user_id,
            metadata={"matched": False},
            commit=True,
        )
        return None

    person, identity = row
    if identity.status != "ACTIVE":
        record_audit(
            db,
            action="NATIONAL_IDENTITY_LOOKUP",
            resource_type="AFYA_ID",
            resource_id=_audit_identifier(normalized),
            result="IDENTITY_INACTIVE",
            user_id=actor_user_id,
            metadata={"matched": False, "identity_status": identity.status},
            commit=True,
        )
        return None

    record_audit(
        db,
        action="NATIONAL_IDENTITY_LOOKUP",
        resource_type="PERSON",
        resource_id=str(person.id),
        result="SUCCESS",
        user_id=actor_user_id,
        patient_id=person.id,
        metadata={"identity_status": identity.status},
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
        identity_status=identity.status,
    )
