"""Data Protection Act — data subject transparency package."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.consent.models import SensitiveDiseaseConsent
from app.patients.models import AfyaIdentity, Person


def build_privacy_package(db: Session, *, person_id: UUID) -> dict:
    """What AfyaSync holds about a person — for transparency / DPA access request."""
    person = db.get(Person, person_id)
    if person is None:
        raise ValueError("PERSON_NOT_FOUND")

    identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person_id))
    consent_count = db.scalar(
        select(func.count()).select_from(SensitiveDiseaseConsent).where(
            SensitiveDiseaseConsent.patient_id == person_id
        )
    ) or 0
    access_events = db.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.patient_id == person_id)
    ) or 0

    return {
        "data_controller_note": "Facility operators act as data controllers for care records; AfyaSync is the processing platform",
        "person": {
            "id": str(person.id),
            "status": person.status,
            "has_afya_id": bool(identity and identity.status == "ACTIVE"),
            "afya_id": identity.afya_id if identity and identity.status == "ACTIVE" else None,
            "contact_phone_on_file": bool(person.phone),
            "contact_email_on_file": bool(person.email),
            # Never return full national ID — only whether a hash exists
            "national_id_hash_present": bool(person.national_id_hash),
        },
        "rights_summary": {
            "access": "Citizen portal timeline + this package",
            "correction": "Identity correction workflow (maker-checker)",
            "sensitive_disclosure": "Explicit consent_given with signature before cross-facility share",
            "object_to_processing": "Facility-level policy; contact facility DPO",
        },
        "processing_counts": {
            "sensitive_consents": int(consent_count),
            "audit_events_linked": int(access_events),
        },
        "legal_basis_examples": [
            "Healthcare provision",
            "Legal obligation (claims / public health reporting where required)",
            "Consent for sensitive category disclosure",
        ],
        "developer": "BAHATI GAD WANGWE",
    }
