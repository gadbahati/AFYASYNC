from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.consent.models import SensitiveDiseaseConsent
from app.patients.models import PatientFacility, Person
from app.patients.record_service import get_patient_record_summary


def get_cross_facility_record(
    db: Session,
    *,
    patient_id: UUID,
    facility_ids: list[UUID],
    requesting_facility_id: UUID,
    actor_user_id: UUID,
    access_reason: str,
) -> dict | None:
    reason = " ".join(access_reason.split())
    if len(reason) < 3 or len(reason) > 200:
        raise ValueError("INVALID_ACCESS_REASON")
    if not facility_ids:
        raise ValueError("NO_AUTHORIZED_FACILITIES")

    memberships = list(
        db.scalars(
            select(PatientFacility).where(
                PatientFacility.patient_id == patient_id,
                PatientFacility.facility_id.in_(facility_ids),
                PatientFacility.status == "ACTIVE",
            )
        ).all()
    )
    if not memberships:
        return None

    records = []
    for membership in memberships:
        record = get_patient_record_summary(db, patient_id, membership.facility_id)
        if not record:
            continue

        # Cross-facility sensitive diagnoses require explicit patient consent.
        diagnosis_ids = {
            UUID(d["id"])
            for encounter in record.get("encounters", [])
            for d in encounter.get("diagnoses", [])
            if d.get("id")
        }
        allowed_ids = set(
            db.scalars(
                select(SensitiveDiseaseConsent.diagnosis_id).where(
                    SensitiveDiseaseConsent.patient_id == patient_id,
                    SensitiveDiseaseConsent.diagnosis_id.in_(diagnosis_ids),
                    SensitiveDiseaseConsent.consent_given.is_(True),
                    SensitiveDiseaseConsent.share_scope == "CROSS_FACILITY",
                )
            ).all()
        )
        if membership.facility_id != requesting_facility_id:
            for encounter in record.get("encounters", []):
                encounter["diagnoses"] = [
                    d for d in encounter.get("diagnoses", []) if UUID(d["id"]) in allowed_ids
                ]

        records.append({
            "facility_id": str(membership.facility_id),
            "record": record,
        })

    if not records:
        return None

    record_audit(
        db,
        action="CROSS_FACILITY_PATIENT_RECORD_READ",
        resource_type="PERSON",
        resource_id=str(patient_id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=requesting_facility_id,
        patient_id=patient_id,
        metadata={
            "source_facility_count": len(records),
            "authorized_facility_count": len(facility_ids),
            "access_reason_length": len(reason),
        },
        commit=True,
    )
    return {
        "patient_id": str(patient_id),
        "access_reason": reason,
        "source_facility_count": len(records),
        "records": records,
    }
