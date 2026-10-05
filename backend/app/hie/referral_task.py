"""FHIR-native representation of AfyaSync referrals using Kenya Core Task.

The local Referral row remains the authoritative workflow state. This module
projects that state into a Kenya Core Task and supporting ServiceRequest for
interoperability; it does not create a second workflow engine.
"""
from __future__ import annotations

from datetime import timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import actor_provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.patients.models import Person
from app.referrals.models import Referral


KENYA_CORE_TASK_PROFILE = (
    "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-task|1.0.0"
)
KENYA_CORE_SERVICEREQUEST_PROFILE = (
    "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-servicerequest|1.0.0"
)
HL7_SERVICE_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/service-type"
REFERRAL_SERVICE_TYPE_CODE = "56"
REFERRAL_SERVICE_TYPE_DISPLAY = "Health Information/Referral"


class ReferralTaskError(ValueError):
    pass


_STATUS = {
    "CREATED": "requested",
    "SENT": "requested",
    "ACCEPTED": "accepted",
    "IN_PROGRESS": "in-progress",
    "COMPLETED": "completed",
    "DECLINED": "failed",
    "CANCELLED": "cancelled",
}

_PRIORITY = {
    "ROUTINE": "routine",
    "URGENT": "urgent",
    "EMERGENCY": "stat",
}


def _get_referral(db: Session, referral_id: UUID, facility_id: UUID) -> Referral:
    referral = db.get(Referral, referral_id)
    if referral is None:
        raise ReferralTaskError("REFERRAL_NOT_FOUND")
    if facility_id not in {referral.source_facility_id, referral.destination_facility_id}:
        raise ReferralTaskError("FACILITY_ACCESS_DENIED")
    return referral


def build_referral_fhir_bundle(
    db: Session,
    *,
    referral_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None,
) -> dict:
    referral = _get_referral(db, referral_id, facility_id)
    person = db.get(Person, referral.patient_id)
    encounter = db.get(Encounter, referral.encounter_id)
    if person is None:
        raise ReferralTaskError("PATIENT_NOT_FOUND")
    if encounter is None or encounter.facility_id != referral.source_facility_id:
        raise ReferralTaskError("ENCOUNTER_NOT_FOUND")

    source_org = _facility_organization_resource(db, referral.source_facility_id)
    destination_org = _facility_organization_resource(db, referral.destination_facility_id)
    patient = _patient_resource(db, person)
    patient["meta"] = {
        "profile": [
            "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"
        ]
    }

    provider_resources = actor_provider_identity_resources(
        db, user_id=actor_user_id, facility_id=referral.source_facility_id
    )
    practitioner_role = next(
        (r for r in provider_resources if r.get("resourceType") == "PractitionerRole"),
        None,
    )

    authored = referral.created_at
    if authored is None:
        raise ReferralTaskError("REFERRAL_AUTHORED_AT_REQUIRED")
    authored_iso = authored.astimezone(timezone.utc).isoformat()

    service_request = {
        "resourceType": "ServiceRequest",
        "id": f"referral-{referral.id}",
        "meta": {"profile": [KENYA_CORE_SERVICEREQUEST_PROFILE]},
        "status": {
            "CREATED": "active",
            "SENT": "active",
            "ACCEPTED": "active",
            "IN_PROGRESS": "active",
            "COMPLETED": "completed",
            "DECLINED": "revoked",
            "CANCELLED": "revoked",
        }.get(referral.status, "active"),
        "intent": "order",
        "priority": _PRIORITY.get(referral.priority, "routine"),
        "subject": {"reference": f"Patient/{person.id}"},
        "encounter": {"reference": f"Encounter/{encounter.id}"},
        "code": {
            "coding": [
                {
                    "system": HL7_SERVICE_TYPE_SYSTEM,
                    "code": REFERRAL_SERVICE_TYPE_CODE,
                    "display": REFERRAL_SERVICE_TYPE_DISPLAY,
                }
            ],
            "text": referral.reason,
        },
        "authoredOn": authored_iso,
        "requester": (
            {"reference": f"PractitionerRole/{practitioner_role['id']}"}
            if practitioner_role
            else {"reference": f"Organization/{referral.source_facility_id}"}
        ),
        "performer": [
            {"reference": f"Organization/{referral.destination_facility_id}"}
        ],
    }
    if referral.clinical_summary:
        service_request["note"] = [{"text": referral.clinical_summary}]

    task = {
        "resourceType": "Task",
        "id": f"referral-task-{referral.id}",
        "meta": {"profile": [KENYA_CORE_TASK_PROFILE]},
        "identifier": [
            {
                "use": "official",
                "type": {"text": "AfyaSync referral identifier"},
                "system": "https://afyasync.health.ke/fhir/referrals",
                "value": referral.referral_id,
            }
        ],
        "status": _STATUS.get(referral.status, "requested"),
        "intent": "order",
        "priority": _PRIORITY.get(referral.priority, "routine"),
        "code": {
            "coding": [
                {
                    "system": HL7_SERVICE_TYPE_SYSTEM,
                    "code": REFERRAL_SERVICE_TYPE_CODE,
                    "display": REFERRAL_SERVICE_TYPE_DISPLAY,
                }
            ],
            "text": "Referral coordination and fulfilment",
        },
        "description": referral.reason,
        "focus": {"reference": f"ServiceRequest/{service_request['id']}"},
        "for": {"reference": f"Patient/{person.id}"},
        "encounter": {"reference": f"Encounter/{encounter.id}"},
        "authoredOn": authored_iso,
        "owner": {"reference": f"Organization/{referral.destination_facility_id}"},
    }

    if referral.status == "COMPLETED":
        task["executionPeriod"] = {
            "start": authored_iso,
            "end": (referral.updated_at or referral.created_at).astimezone(
                timezone.utc
            ).isoformat(),
        }

    provenance = {
        "resourceType": "Provenance",
        "id": f"referral-provenance-{referral.id}",
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"
            ]
        },
        "target": [
            {"reference": f"ServiceRequest/{service_request['id']}"},
            {"reference": f"Task/{task['id']}"},
        ],
        "recorded": authored_iso,
        "agent": [
            (
                {"type": {"text": "author"}, "who": {"reference": f"PractitionerRole/{practitioner_role['id']}"}}
                if practitioner_role
                else {"type": {"text": "author"}, "who": {"reference": f"Organization/{referral.source_facility_id}"}}
            )
        ],
        "reason": [{"text": "National referral coordination"}],
    }

    resources = [
        patient,
        source_org,
        destination_org,
        *provider_resources,
        service_request,
        task,
        provenance,
    ]
    entries = [
        {
            "fullUrl": f"urn:uuid:{resource['resourceType']}/{resource['id']}",
            "resource": resource,
        }
        for resource in resources
    ]
    bundle = {
        "resourceType": "Bundle",
        "id": f"referral-fhir-{referral.id}",
        "type": "collection",
        "entry": entries,
    }
    try:
        assert_valid_bundle(bundle)
    except ValueError as exc:
        raise ReferralTaskError(str(exc)) from exc
    return bundle
