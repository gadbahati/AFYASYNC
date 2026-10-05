"""Phase 184: FHIR CareTeam projection for AfyaSync care coordination cases.

The persisted CareCoordinationCase remains authoritative. This module only
projects the existing care-coordination participants into FHIR.
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


class CareTeamFhirError(ValueError):
    pass


CARETEAM_STATUS = {
    "OPEN": "active",
    "ACCEPTED": "active",
    "SCHEDULED": "active",
    "HANDED_OFF": "active",
    "COMPLETED": "completed",
    "CANCELLED": "inactive",
    "OVERDUE": "active",
}


def build_care_team_bundle(
    db: Session,
    *,
    case_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None,
) -> dict:
    case = db.get(CareCoordinationCase, case_id)
    if case is None:
        raise CareTeamFhirError("CASE_NOT_FOUND")

    if facility_id not in {case.source_facility_id, case.destination_facility_id}:
        raise CareTeamFhirError("FACILITY_ACCESS_DENIED")

    referral = db.get(Referral, case.referral_id)
    if referral is None:
        raise CareTeamFhirError("REFERRAL_NOT_FOUND")

    person = db.get(Person, case.patient_id)
    if person is None:
        raise CareTeamFhirError("PATIENT_NOT_FOUND")

    encounter = db.get(Encounter, referral.encounter_id) if referral.encounter_id else None
    if encounter is None or encounter.facility_id != case.source_facility_id:
        raise CareTeamFhirError("ENCOUNTER_NOT_FOUND")

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

    member = [
        {"entity": {"reference": f"Organization/{case.source_facility_id}"}},
        {"entity": {"reference": f"Organization/{case.destination_facility_id}"}},
    ]
    for resource in providers:
        if resource.get("resourceType") in {"Practitioner", "PractitionerRole"}:
            member.append(
                {
                    "entity": {
                        "reference": f"{resource['resourceType']}/{resource['id']}"
                    }
                }
            )

    recorded = case.updated_at or case.created_at
    if not recorded:
        raise CareTeamFhirError("CASE_CREATED_AT_REQUIRED")

    recorded_iso = recorded.astimezone(timezone.utc).isoformat()

    care_team = {
        "resourceType": "CareTeam",
        "id": f"care-team-{case.id}",
        "identifier": [
            {
                "use": "official",
                "system": "https://afyasync.health.ke/fhir/care-coordination",
                "value": case.case_number,
            }
        ],
        "status": CARETEAM_STATUS.get(case.status, "active"),
        "name": "Care coordination team",
        "subject": {"reference": f"Patient/{person.id}"},
        "encounter": {"reference": f"Encounter/{encounter.id}"},
        "period": {
            "start": case.created_at.astimezone(timezone.utc).isoformat()
            if case.created_at
            else recorded_iso
        },
        "participant": member,
    }

    if case.closed_at or case.handoff_at:
        care_team["period"]["end"] = (
            (case.closed_at or case.handoff_at)
            .astimezone(timezone.utc)
            .isoformat()
        )

    if case.notes or referral.reason:
        care_team["note"] = [
            {"text": case.notes or referral.reason}
        ]

    provenance = {
        "resourceType": "Provenance",
        "id": f"care-team-provenance-{case.id}",
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"
            ]
        },
        "target": [{"reference": f"CareTeam/{care_team['id']}"}],
        "recorded": recorded_iso,
        "agent": [
            {
                "type": {"text": "care coordination actor"},
                "who": (
                    {"reference": f"PractitionerRole/{r['id']}"}
                    if r.get("resourceType") == "PractitionerRole"
                    else {"reference": f"Practitioner/{r['id']}"}
                ),
            }
            for r in providers
        ]
        or [
            {
                "type": {"text": "care coordination facility"},
                "who": {"reference": f"Organization/{facility_id}"},
            }
        ],
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
            "serviceProvider": {
                "reference": f"Organization/{encounter.facility_id}"
            },
        },
        care_team,
        provenance,
    ]

    bundle = {
        "resourceType": "Bundle",
        "id": f"care-team-fhir-{case.id}",
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
        raise CareTeamFhirError(str(exc)) from exc

    return bundle
