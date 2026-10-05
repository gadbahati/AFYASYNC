"""FHIR Observation interoperability for persisted AfyaSync triage assessments."""
from datetime import timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import TriageAssessment
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.hie.terminology_service import canonical_coding
from app.patients.models import Person
from app.rbac.models import Staff, User

OBSERVATION_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-observation|1.0.0"
PROVENANCE_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"


class TriageObservationFhirError(ValueError):
    pass


def build_triage_observation_bundle(
    db: Session, *, triage_id: UUID, facility_id: UUID, actor_user_id: UUID | None = None
) -> dict:
    triage = db.get(TriageAssessment, triage_id)
    if triage is None:
        raise TriageObservationFhirError("TRIAGE_NOT_FOUND")

    encounter = db.get(Encounter, triage.encounter_id)
    if encounter is None:
        raise TriageObservationFhirError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise TriageObservationFhirError("ACCESS_DENIED")

    person = db.get(Person, encounter.patient_id)
    if person is None:
        raise TriageObservationFhirError("PATIENT_NOT_FOUND")

    coding = canonical_coding(
        db, source_system="AFYASYNC:TRIAGE", source_code=str(triage.acuity), display="Triage acuity"
    )
    if not coding:
        raise TriageObservationFhirError(f"TRIAGE_ACUITY_NOT_MAPPED:{triage.acuity}")

    patient = _patient_resource(db, person)
    patient["meta"] = {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"]}
    facility = _facility_organization_resource(db, facility_id)

    providers = []
    if triage.assessed_by:
        staff = db.scalar(select(Staff).where(
            Staff.id == triage.assessed_by,
            Staff.facility_id == facility_id,
            Staff.status == "ACTIVE",
        ))
        if staff:
            providers = provider_identity_resources(db, facility_id=facility_id, staff_id=staff.id)

    performer = next(
        ({"reference": f'PractitionerRole/{item["id"]}'} for item in providers if item.get("resourceType") == "PractitionerRole"),
        {"reference": f"Organization/{facility_id}"},
    )

    recorded_dt = triage.assessed_at
    if recorded_dt is None:
        raise TriageObservationFhirError("TRIAGE_ASSESSED_AT_REQUIRED")
    recorded = recorded_dt.astimezone(timezone.utc).isoformat()

    observation = {
        "resourceType": "Observation",
        "id": str(triage.id),
        "meta": {"profile": [OBSERVATION_PROFILE]},
        "status": "final",
        "category": [{"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "survey",
        }]}],
        "code": {"coding": [coding], "text": "Triage acuity"},
        "subject": {"reference": f"Patient/{person.id}"},
        "encounter": {"reference": f"Encounter/{encounter.id}"},
        "effectiveDateTime": recorded,
        "performer": [performer],
        "valueCodeableConcept": {"coding": [coding], "text": str(triage.acuity)},
    }
    if triage.chief_complaint:
        observation["note"] = [{"text": f"Chief complaint: {triage.chief_complaint}"}]
    if triage.notes:
        observation.setdefault("note", []).append({"text": triage.notes})

    provenance = {
        "resourceType": "Provenance",
        "id": f"triage-provenance-{triage.id}",
        "meta": {"profile": [PROVENANCE_PROFILE]},
        "target": [{"reference": f"Observation/{triage.id}"}],
        "recorded": recorded,
        "agent": [{"type": {"text": "recorder"}, "who": performer}],
    }

    resources = [patient, facility, *providers, observation, provenance]
    bundle = {
        "resourceType": "Bundle",
        "id": f"triage-fhir-{triage.id}",
        "type": "collection",
        "entry": [
            {"fullUrl": f'urn:uuid:{item["resourceType"]}/{item["id"]}', "resource": item}
            for item in resources
        ],
    }
    try:
        assert_valid_bundle(bundle)
    except ValueError as exc:
        raise TriageObservationFhirError(str(exc)) from exc

    record_audit(
        db, action="HIE_TRIAGE_OBSERVATION_EXPORT", resource_type="TRIAGE_ASSESSMENT",
        resource_id=str(triage.id), result="SUCCESS", user_id=actor_user_id,
        facility_id=facility_id, patient_id=person.id,
        metadata={"acuity": triage.acuity}, commit=False,
    )
    return bundle
