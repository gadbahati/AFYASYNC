"""Phase 183: FHIR CarePlan projection for AfyaSync care coordination cases.

The persisted CareCoordinationCase remains the authoritative workflow. This
module only projects that state into FHIR for interoperability.
"""
from __future__ import annotations

from datetime import timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.care_coordination.models import CareCoordinationCase
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import actor_provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.patients.models import Person
from app.referrals.models import Referral


class CarePlanFhirError(ValueError):
    pass


CAREPLAN_STATUS = {
    "OPEN": "active",
    "ACCEPTED": "active",
    "SCHEDULED": "active",
    "HANDED_OFF": "active",
    "COMPLETED": "completed",
    "CANCELLED": "revoked",
    "OVERDUE": "active",
}


def build_care_plan_bundle(
    db: Session,
    *,
    case_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None,
) -> dict:
    case = db.get(CareCoordinationCase, case_id)
    if case is None:
        raise CarePlanFhirError("CASE_NOT_FOUND")

    if facility_id not in {case.source_facility_id, case.destination_facility_id}:
        raise CarePlanFhirError("FACILITY_ACCESS_DENIED")

    referral = db.get(Referral, case.referral_id)
    if referral is None:
        raise CarePlanFhirError("REFERRAL_NOT_FOUND")

    person = db.get(Person, case.patient_id)
    if person is None:
        raise CarePlanFhirError("PATIENT_NOT_FOUND")

    encounter = db.get(Encounter, referral.encounter_id) if referral.encounter_id else None
    if encounter is None or encounter.facility_id != case.source_facility_id:
        raise CarePlanFhirError("ENCOUNTER_NOT_FOUND")

    if not case.created_at:
        raise CarePlanFhirError("CASE_CREATED_AT_REQUIRED")

    source_org = _facility_organization_resource(db, case.source_facility_id)
    destination_org = _facility_organization_resource(db, case.destination_facility_id)

    patient = _patient_resource(db, person)
    patient["meta"] = {
        "profile": [
            "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"
        ]
    }

    providers = actor_provider_identity_resources(
        db,
        user_id=actor_user_id,
        facility_id=facility_id,
    )
    practitioner_role = next(
        (r for r in providers if r.get("resourceType") == "PractitionerRole"),
        None,
    )

    authored = case.created_at.astimezone(timezone.utc).isoformat()
    updated = (case.closed_at or case.handoff_at or case.appointment_at or case.updated_at)
    updated_iso = updated.astimezone(timezone.utc).isoformat() if updated else authored

    care_plan = {
        "resourceType": "CarePlan",
        "id": f"care-plan-{case.id}",
        "identifier": [
            {
                "use": "official",
                "type": {"text": "AfyaSync care coordination case"},
                "system": "https://afyasync.health.ke/fhir/care-coordination",
                "value": case.case_number,
            }
        ],
        "status": CAREPLAN_STATUS.get(case.status, "active"),
        "intent": "plan",
        "title": "Care coordination plan",
        "description": case.notes or referral.clinical_summary or referral.reason,
        "subject": {"reference": f"Patient/{person.id}"},
        "encounter": {"reference": f"Encounter/{encounter.id}"},
        "created": authored,
        "period": {"start": authored},
        "author": (
            {"reference": f"PractitionerRole/{practitioner_role['id']}"}
            if practitioner_role
            else {"reference": f"Organization/{case.source_facility_id}"}
        ),
        "careTeam": [
            {"reference": f"Organization/{case.source_facility_id}"},
            {"reference": f"Organization/{case.destination_facility_id}"},
        ],
        "activity": [
            {
                "detail": {
                    "status": "completed" if case.status == "COMPLETED" else "scheduled" if case.status == "SCHEDULED" else "in-progress",
                    "description": referral.reason or "Care coordination and referral follow-up",
                    "scheduledDate": case.appointment_at.astimezone(timezone.utc).isoformat()
                    if case.appointment_at
                    else None,
                    "performer": [
                        {"reference": f"Organization/{case.destination_facility_id}"}
                    ],
                }
            }
        ],
    }
    if case.closed_at or case.handoff_at:
        care_plan["period"]["end"] = (
            (case.closed_at or case.handoff_at).astimezone(timezone.utc).isoformat()
        )
    if case.due_at:
        care_plan["note"] = [{"text": f"Care coordination due: {case.due_at.astimezone(timezone.utc).isoformat()}"}]
    if case.outcome:
        care_plan["note"] = care_plan.get("note", []) + [{"text": f"Outcome: {case.outcome}"}]

    provenance = {
        "resourceType": "Provenance",
        "id": f"care-plan-provenance-{case.id}",
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"
            ]
        },
        "target": [{"reference": f"CarePlan/{care_plan['id']}"}],
        "recorded": updated_iso,
        "agent": [
            (
                {
                    "type": {"text": "care coordination actor"},
                    "who": {"reference": f"PractitionerRole/{practitioner_role['id']}"},
                }
                if practitioner_role
                else {
                    "type": {"text": "care coordination facility"},
                    "who": {"reference": f"Organization/{facility_id}"},
                }
            )
        ],
        "reason": [{"text": "Care coordination interoperability"}],
    }

    resources = [
        patient,
        source_org,
        destination_org,
        *providers,
        {
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
            "serviceProvider": {"reference": f"Organization/{encounter.facility_id}"},
        },
        care_plan,
        provenance,
    ]

    bundle = {
        "resourceType": "Bundle",
        "id": f"care-plan-fhir-{case.id}",
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
        raise CarePlanFhirError(str(exc)) from exc

    return bundle
