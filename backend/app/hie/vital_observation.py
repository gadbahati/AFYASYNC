"""FHIR Observation interoperability for persisted AfyaSync vital signs.

Vital observations use explicit terminology-registry mappings. No national or
external coding is fabricated by this projection.
"""
from __future__ import annotations

from datetime import timezone
from uuid import UUID, uuid4

from app.audit.service import record_audit
from app.clinical.models import Vital
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.hie.terminology_service import canonical_coding
from app.patients.models import Person
from sqlalchemy.orm import Session


class VitalObservationFhirError(ValueError):
    pass


_FIELDS = (
    ("temperature_c", "temperature"),
    ("pulse", "pulse"),
    ("bp_systolic", "blood-pressure-systolic"),
    ("bp_diastolic", "blood-pressure-diastolic"),
    ("spo2", "oxygen-saturation"),
    ("respiratory_rate", "respiratory-rate"),
    ("weight_kg", "body-weight"),
)


def build_vital_observation_bundle(
    db: Session,
    *,
    vital_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    vital = db.get(Vital, vital_id)
    if vital is None:
        raise VitalObservationFhirError("VITAL_NOT_FOUND")

    encounter = db.get(Encounter, vital.encounter_id)
    if encounter is None:
        raise VitalObservationFhirError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise VitalObservationFhirError("ACCESS_DENIED")

    person = db.get(Person, encounter.patient_id)
    if person is None:
        raise VitalObservationFhirError("PATIENT_NOT_FOUND")

    facility = _facility_organization_resource(db, facility_id)
    patient = _patient_resource(db, person)
    providers = (
        provider_identity_resources(
            db, facility_id=facility_id, staff_id=vital.recorded_by
        )
        if vital.recorded_by
        else []
    )
    role = next((r for r in providers if r.get("resourceType") == "PractitionerRole"), None)
    performer_ref = (
        {"reference": f"PractitionerRole/{role['id']}"}
        if role
        else {"reference": f"Organization/{facility_id}"}
    )

    recorded = (
        vital.recorded_at.astimezone(timezone.utc).isoformat()
        if vital.recorded_at
        else None
    )
    if not recorded:
        raise VitalObservationFhirError("VITAL_TIMESTAMP_REQUIRED")

    entries = [
        {"fullUrl": f"urn:uuid:{patient['id']}", "resource": patient},
        {"fullUrl": f"urn:uuid:{facility['id']}", "resource": facility},
        *[
            {
                "fullUrl": f"urn:uuid:{resource['resourceType']}/{resource['id']}",
                "resource": resource,
            }
            for resource in providers
        ],
    ]

    observations = []
    for field, source_code in _FIELDS:
        raw = getattr(vital, field)
        if raw is None or str(raw).strip() == "":
            continue
        coding = canonical_coding(
            db,
            source_system="AFYASYNC:VITAL",
            source_code=source_code,
            display=source_code.replace("-", " ").title(),
        )
        if coding is None:
            raise VitalObservationFhirError(f"VITAL_CODE_NOT_MAPPED:{source_code}")

        observation = {
            "resourceType": "Observation",
            "id": str(uuid4()),
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs",
                }],
                "text": "Vital Signs",
            }],
            "code": {"coding": [coding], "text": source_code.replace("-", " ").title()},
            "subject": {"reference": f"Patient/{person.id}"},
            "encounter": {"reference": f"Encounter/{encounter.id}"},
            "effectiveDateTime": recorded,
            "performer": [performer_ref],
            "valueString": str(raw),
        }
        observations.append(observation)
        entries.append({
            "fullUrl": f"urn:uuid:{observation['id']}",
            "resource": observation,
        })

    if not observations:
        raise VitalObservationFhirError("VITAL_VALUES_REQUIRED")

    provenance = {
        "resourceType": "Provenance",
        "id": str(uuid4()),
        "target": [{"reference": f"Observation/{o['id']}"} for o in observations],
        "recorded": recorded,
        "agent": [{
            "type": {"text": "recorder"},
            "who": performer_ref,
            "onBehalfOf": {"reference": f"Organization/{facility_id}"},
        }],
        "activity": {"text": "HIE vital observation export"},
    }
    entries.append({
        "fullUrl": f"urn:uuid:{provenance['id']}",
        "resource": provenance,
    })

    bundle = {
        "resourceType": "Bundle",
        "id": str(uuid4()),
        "type": "collection",
        "timestamp": recorded,
        "total": len(entries),
        "entry": entries,
        "meta": {"tag": [{
            "system": "https://afyasync.health.ke/hie",
            "code": "VITAL_OBSERVATIONS",
        }]},
    }
    try:
        assert_valid_bundle(bundle)
    except ValueError as exc:
        raise VitalObservationFhirError(str(exc)) from exc

    record_audit(
        db,
        action="HIE_VITAL_OBSERVATION_EXPORT",
        resource_type="VITAL",
        resource_id=str(vital.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person.id,
        metadata={"observation_count": len(observations)},
        commit=False,
    )
    return bundle
