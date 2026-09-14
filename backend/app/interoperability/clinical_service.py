from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.encounters.models import Encounter
from app.interoperability.clinical_schemas import (
    FHIRBundleEntry,
    FHIRBundleResource,
    FHIREncounterResource,
)
from app.interoperability.service import get_fhir_patient


def get_fhir_clinical_bundle(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID,
    access_reason: str,
) -> FHIRBundleResource:
    reason = " ".join(access_reason.split())
    if len(reason) < 3 or len(reason) > 200:
        raise ValueError("INVALID_ACCESS_REASON")

    patient = get_fhir_patient(
        db,
        patient_id=patient_id,
        facility_id=facility_id,
        actor_user_id=actor_user_id,
    )
    encounters = list(
        db.scalars(
            select(Encounter)
            .where(
                Encounter.patient_id == patient_id,
                Encounter.facility_id == facility_id,
            )
            .order_by(Encounter.started_at.desc(), Encounter.id.desc())
            .limit(100)
        )
    )

    entries = [
        FHIRBundleEntry(fullUrl=f"urn:uuid:{patient.id}", resource=patient)
    ]
    entries.extend(
        FHIRBundleEntry(
            fullUrl=f"urn:uuid:{encounter.id}",
            resource=FHIREncounterResource(
                id=encounter.id,
                status=encounter.status,
                class_code=encounter.encounter_type,
                period_start=encounter.started_at,
                period_end=encounter.ended_at,
                patient_id=encounter.patient_id,
            ),
        )
        for encounter in encounters
    )

    record_audit(
        db,
        action="INTEROPERABILITY_CLINICAL_READ",
        resource_type="PERSON",
        resource_id=str(patient_id),
        result="SUCCESS",
        user_id=actor_user_id,
        patient_id=patient_id,
        metadata={
            "facility_id": str(facility_id),
            "format": "FHIR_MINIMAL_BUNDLE",
            "encounter_count": len(encounters),
            "reason_length": len(reason),
        },
        commit=True,
    )
    return FHIRBundleResource(total=len(entries), entry=entries)
