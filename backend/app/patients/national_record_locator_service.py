import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.facilities.models import Facility
from app.patients.models import AfyaIdentity, PatientFacility, Person
from app.patients.national_record_locator_schemas import NationalRecordFacility, NationalRecordLocatorResponse


def _audit_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _reason_metadata(reason: str) -> dict[str, str | int]:
    """Prove a purpose was supplied without persisting free-text purpose content."""
    normalized = reason.strip()
    return {
        "access_reason_hash": _audit_identifier(normalized),
        "access_reason_length": len(normalized),
    }


def locate_national_records(
    db: Session,
    afya_id: str,
    *,
    access_reason: str,
    actor_user_id: UUID,
) -> NationalRecordLocatorResponse | None:
    normalized = afya_id.strip().upper()
    reason = access_reason.strip()
    if not normalized or len(reason) < 5:
        return None

    identity_row = db.execute(
        select(Person, AfyaIdentity)
        .join(AfyaIdentity, AfyaIdentity.person_id == Person.id)
        .where(AfyaIdentity.afya_id == normalized)
    ).first()

    audit_id = _audit_identifier(normalized)
    if identity_row is None:
        record_audit(
            db,
            action="NATIONAL_RECORD_LOCATOR",
            resource_type="AFYA_ID",
            resource_id=audit_id,
            result="NOT_FOUND",
            user_id=actor_user_id,
            metadata={"matched": False, **_reason_metadata(reason)},
            commit=True,
        )
        return None

    person, identity = identity_row
    if identity.status != "ACTIVE" or person.status != "ACTIVE":
        record_audit(
            db,
            action="NATIONAL_RECORD_LOCATOR",
            resource_type="AFYA_ID",
            resource_id=audit_id,
            result="IDENTITY_INACTIVE",
            user_id=actor_user_id,
            metadata={
                "matched": False,
                "identity_status": identity.status,
                "patient_status": person.status,
                **_reason_metadata(reason),
            },
            commit=True,
        )
        return None

    rows = db.execute(
        select(PatientFacility, Facility)
        .join(Facility, Facility.id == PatientFacility.facility_id)
        .where(
            PatientFacility.patient_id == person.id,
            PatientFacility.status == "ACTIVE",
            Facility.status == "ACTIVE",
        )
        .order_by(Facility.name, Facility.facility_id)
    ).all()

    facilities = [
        NationalRecordFacility(
            facility_id=facility.id,
            facility_code=facility.facility_id,
            facility_name=facility.name,
            county=facility.county,
            enrollment_status=link.status,
        )
        for link, facility in rows
    ]

    record_audit(
        db,
        action="NATIONAL_RECORD_LOCATOR",
        resource_type="PERSON",
        resource_id=str(person.id),
        result="SUCCESS",
        user_id=actor_user_id,
        patient_id=person.id,
        metadata={"facility_count": len(facilities), **_reason_metadata(reason)},
        commit=True,
    )

    return NationalRecordLocatorResponse(
        afya_id=identity.afya_id,
        person_id=person.id,
        record_status=person.status,
        facilities=facilities,
    )
