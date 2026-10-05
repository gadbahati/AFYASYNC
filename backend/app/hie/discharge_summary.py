"""Phase 191: FHIR discharge summary interoperability.

Projects the persisted AfyaSync ClinicalDischarge record into a FHIR
Composition document bundle. No unverified Kenya profile is asserted.
"""
from __future__ import annotations

from datetime import timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.discharge_models import ClinicalDischarge
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.patients.models import Person


KENYA_CORE_PROVENANCE_PROFILE = (
    "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"
)


class DischargeFhirError(ValueError):
    pass


def build_discharge_summary_bundle(
    db: Session,
    *,
    discharge_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    discharge = db.get(ClinicalDischarge, discharge_id)
    if discharge is None:
        raise DischargeFhirError("DISCHARGE_NOT_FOUND")
    if discharge.facility_id != facility_id:
        raise DischargeFhirError("ACCESS_DENIED")

    encounter = db.get(Encounter, discharge.encounter_id)
    if encounter is None:
        raise DischargeFhirError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id or encounter.patient_id != discharge.patient_id:
        raise DischargeFhirError("ACCESS_DENIED")

    person = db.get(Person, discharge.patient_id)
    if person is None:
        raise DischargeFhirError("PATIENT_NOT_FOUND")

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
            staff_id=discharge.discharged_by,
        )
        if discharge.discharged_by
        else []
    )
    role = next(
        (r for r in providers if r.get("resourceType") == "PractitionerRole"),
        None,
    )
    author = (
        {"reference": f"PractitionerRole/{role['id']}"}
        if role
        else {"reference": f"Organization/{facility_id}"}
    )

    discharged_at = discharge.discharged_at.astimezone(timezone.utc).isoformat()
    composition_id = f"discharge-summary-{discharge.id}"

    sections = [
        {
            "title": "Discharge outcome",
            "code": {"text": "Discharge outcome"},
            "text": {
                "status": "generated",
                "div": (
                    f"<div><p>Disposition: {discharge.disposition}</p>"
                    f"<p>Outcome: {discharge.outcome}</p></div>"
                ),
            },
        }
    ]
    if discharge.discharge_summary:
        sections.append(
            {
                "title": "Clinical discharge summary",
                "code": {"text": "Clinical discharge summary"},
                "text": {
                    "status": "generated",
                    "div": f"<div><p>{discharge.discharge_summary}</p></div>",
                },
            }
        )
    if discharge.follow_up_instructions or discharge.follow_up_date:
        follow_text = discharge.follow_up_instructions or ""
        if discharge.follow_up_date:
            follow_text = (follow_text + " " if follow_text else "") + (
                f"Follow-up date: {discharge.follow_up_date.isoformat()}."
            )
        sections.append(
            {
                "title": "Follow-up",
                "code": {"text": "Follow-up"},
                "text": {"status": "generated", "div": f"<div><p>{follow_text}</p></div>"},
            }
        )

    composition = {
        "resourceType": "Composition",
        "id": composition_id,
        "status": "final",
        "type": {"text": "Discharge summary"},
        "subject": {"reference": f"Patient/{person.id}"},
        "encounter": {"reference": f"Encounter/{encounter.id}"},
        "date": discharged_at,
        "author": [author],
        "title": "AfyaSync Discharge Summary",
        "custodian": {"reference": f"Organization/{facility_id}"},
        "section": sections,
    }

    encounter_resource = {
        "resourceType": "Encounter",
        "id": str(encounter.id),
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-encounter|1.0.0"
            ]
        },
        "status": (encounter.status or "unknown").lower(),
        "class": {"code": getattr(encounter, "encounter_type", None) or "AMB"},
        "subject": {"reference": f"Patient/{person.id}"},
        "serviceProvider": {"reference": f"Organization/{facility_id}"},
    }

    provenance = {
        "resourceType": "Provenance",
        "id": f"discharge-provenance-{discharge.id}",
        "meta": {"profile": [KENYA_CORE_PROVENANCE_PROFILE]},
        "target": [{"reference": f"Composition/{composition_id}"}],
        "recorded": discharged_at,
        "agent": [{"type": {"text": "discharge author"}, "who": author}],
        "reason": [{"text": "Clinical discharge interoperability"}],
    }

    resources = [composition, patient, facility, *providers, encounter_resource, provenance]
    bundle = {
        "resourceType": "Bundle",
        "id": f"discharge-fhir-{discharge.id}",
        "type": "document",
        "timestamp": discharged_at,
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
        raise DischargeFhirError(str(exc)) from exc

    record_audit(
        db,
        action="HIE_DISCHARGE_SUMMARY_EXPORT",
        resource_type="CLINICAL_DISCHARGE",
        resource_id=str(discharge.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person.id,
        metadata={"bundle_type": "document"},
        commit=False,
    )
    return bundle
