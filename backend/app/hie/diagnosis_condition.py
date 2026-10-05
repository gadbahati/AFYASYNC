"""FHIR Condition interoperability for persisted AfyaSync diagnoses.

Only explicit terminology-registry mappings are exported as coded Conditions.
No national diagnosis code or Kenya profile is fabricated.
"""
from __future__ import annotations

from datetime import timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import Diagnosis
from app.consent.models import SensitiveCategory, SensitiveDiseaseConsent
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.hie.terminology_service import canonical_coding
from app.patients.models import Person


KENYA_CORE_CONDITION_PROFILE = (
    "https://fhir.dha.go.ke/core/StructureDefinition/condition|1.0.0"
)
KENYA_CORE_PROVENANCE_PROFILE = (
    "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"
)


class DiagnosisFhirError(ValueError):
    pass


def build_diagnosis_condition_bundle(
    db: Session,
    *,
    diagnosis_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    diagnosis = db.get(Diagnosis, diagnosis_id)
    if diagnosis is None:
        raise DiagnosisFhirError("DIAGNOSIS_NOT_FOUND")

    encounter = db.get(Encounter, diagnosis.encounter_id)
    if encounter is None:
        raise DiagnosisFhirError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise DiagnosisFhirError("ACCESS_DENIED")

    person = db.get(Person, encounter.patient_id)
    if person is None:
        raise DiagnosisFhirError("PATIENT_NOT_FOUND")

    if not diagnosis.code:
        raise DiagnosisFhirError("DIAGNOSIS_CODE_REQUIRED")

    coding = canonical_coding(
        db,
        source_system="AFYASYNC:DIAGNOSIS",
        source_code=diagnosis.code,
        display=diagnosis.description,
    )
    if not coding:
        raise DiagnosisFhirError(
            f"DIAGNOSIS_CODE_NOT_NATIONALLY_MAPPED:{diagnosis.code}"
        )

    # A diagnosis whose code is explicitly registered as sensitive cannot cross
    # the facility boundary without an affirmative consent record.
    sensitive = db.scalar(
        select(SensitiveCategory.id).where(
            SensitiveCategory.code == diagnosis.code,
            SensitiveCategory.is_active.is_(True),
        )
    )
    if sensitive is not None:
        consent = db.scalar(
            select(SensitiveDiseaseConsent).where(
                SensitiveDiseaseConsent.diagnosis_id == diagnosis.id,
                SensitiveDiseaseConsent.patient_id == person.id,
                SensitiveDiseaseConsent.facility_id == facility_id,
            )
        )
        if consent is None or not consent.consent_given or consent.share_scope != "CROSS_FACILITY":
            raise DiagnosisFhirError("SENSITIVE_DIAGNOSIS_CONSENT_REQUIRED")

    patient = _patient_resource(db, person)
    patient["meta"] = {
        "profile": [
            "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"
        ]
    }
    facility = _facility_organization_resource(db, facility_id)

    providers = (
        provider_identity_resources(
            db,
            facility_id=facility_id,
            staff_id=diagnosis.recorded_by,
        )
        if diagnosis.recorded_by
        else []
    )
    role = next(
        (r for r in providers if r.get("resourceType") == "PractitionerRole"),
        None,
    )
    performer = (
        {"reference": f"PractitionerRole/{role['id']}"}
        if role
        else {"reference": f"Organization/{facility_id}"}
    )

    recorded = diagnosis.recorded_at.astimezone(timezone.utc).isoformat()
    condition = {
        "resourceType": "Condition",
        "id": str(diagnosis.id),
        "meta": {"profile": [KENYA_CORE_CONDITION_PROFILE]},
        "code": {"coding": [coding], "text": diagnosis.description},
        "subject": {"reference": f"Patient/{person.id}"},
        "encounter": {"reference": f"Encounter/{encounter.id}"},
        "recordedDate": recorded,
        "recorder": performer,
    }
    if diagnosis.diagnosis_type:
        condition["note"] = [{"text": f"Diagnosis type: {diagnosis.diagnosis_type}"}]

    provenance = {
        "resourceType": "Provenance",
        "id": f"diagnosis-provenance-{diagnosis.id}",
        "meta": {"profile": [KENYA_CORE_PROVENANCE_PROFILE]},
        "target": [{"reference": f"Condition/{diagnosis.id}"}],
        "recorded": recorded,
        "agent": [{"type": {"text": "recorder"}, "who": performer}],
        "reason": [{"text": "Clinical diagnosis interoperability"}],
    }

    resources = [patient, facility, *providers, condition, provenance]
    bundle = {
        "resourceType": "Bundle",
        "id": f"diagnosis-fhir-{diagnosis.id}",
        "type": "collection",
        "entry": [
            {
                "fullUrl": f"urn:uuid:{resource['resourceType']}/{resource['id']}",
                "resource": resource,
            }
            for resource in resources
        ],
    }

    try:
        assert_valid_bundle(bundle)
    except ValueError as exc:
        raise DiagnosisFhirError(str(exc)) from exc

    record_audit(
        db,
        action="HIE_DIAGNOSIS_CONDITION_EXPORT",
        resource_type="DIAGNOSIS",
        resource_id=str(diagnosis.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person.id,
        metadata={"sensitive": sensitive is not None},
        commit=False,
    )
    return bundle
