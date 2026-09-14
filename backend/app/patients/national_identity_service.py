import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.patients.models import AfyaIdentity, Person
from app.patients.national_identity_schemas import NationalIdentityResolution

_AFYA_ID_PATTERN = re.compile(r"^AF-\d{8}$")


def _audit_identifier(value: str) -> str:
    import hashlib
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_afya_id(value: str) -> str:
    normalized = " ".join(value.split()).upper()
    if not _AFYA_ID_PATTERN.fullmatch(normalized):
        raise ValueError("INVALID_AFYA_ID")
    return normalized


def resolve_national_identity(
    db: Session,
    afya_id: str,
    *,
    actor_user_id: UUID,
    access_reason: str,
) -> NationalIdentityResolution | None:
    normalized = normalize_afya_id(afya_id)
    reason = " ".join(access_reason.split())
    if len(reason) < 5 or len(reason) > 500:
        raise ValueError("INVALID_ACCESS_REASON")

    row = db.execute(
        select(Person, AfyaIdentity)
        .join(AfyaIdentity, AfyaIdentity.person_id == Person.id)
        .where(AfyaIdentity.afya_id == normalized, AfyaIdentity.status == "ACTIVE", Person.status == "ACTIVE")
    ).first()
    if row is None:
        record_audit(db, action="NATIONAL_IDENTITY_LOOKUP", resource_type="AFYA_ID", resource_id=_audit_identifier(normalized), result="NOT_FOUND", user_id=actor_user_id, metadata={"matched": False, "reason_length": len(reason), "requested_at": datetime.now(timezone.utc).isoformat()}, commit=True)
        return None

    person, identity = row
    record_audit(db, action="NATIONAL_IDENTITY_LOOKUP", resource_type="PERSON", resource_id=str(person.id), result="SUCCESS", user_id=actor_user_id, patient_id=person.id, metadata={"identity_status": identity.status, "reason_length": len(reason)}, commit=True)
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
