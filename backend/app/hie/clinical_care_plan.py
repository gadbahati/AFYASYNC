"""FHIR interoperability for facility clinical care plans."""
from __future__ import annotations

from datetime import datetime, time, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import CarePlan
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import actor_provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.patients.models import Person


class ClinicalCarePlanFhirError(ValueError):
    pass


STATUS_MAP = {
    "ACTIVE": "active",
    "COMPLETED": "completed",
    "CANCELLED": "revoked",
}


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _narrative(text: str | None) -> dict | None:
    if not text:
        return None
    from html import escape
    return {"text": {"status": "generated", "div": f"<div>{escape(text)}</div>"}}


def build_clinical_care_plan_bundle(
    db: Session,
    *,
    plan_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    plan = db.get(CarePlan, plan_id)
    if plan is None:
        raise ClinicalCarePlanFhirError("CARE_PLAN_NOT_FOUND")
    if plan.facility_id != facility_id:
        raise ClinicalCarePlanFhirError("ACCESS_DENIED")

    person = db.get(Person, plan.patient_id)
    if person is None:
        raise ClinicalCarePlanFhirError("PATIENT_NOT_FOUND")

    patient = _patient_resource(db, person)
    patient["meta"] = {
        "profile": [
            "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"
        ]
    }
    facility = _facility_organization_resource(db, facility_id)

    encounter_resource = None
    if plan.encounter_id is not None:
        encounter = db.get(Encounter, plan.encounter_id)
        if encounter is None or encounter.facility_id != facility_id or encounter.patient_id != plan.patient_id:
            raise ClinicalCarePlanFhirError("ENCOUNTER_NOT_FOUND")
        encounter_resource = {
            "resourceType": "Encounter",
            "id": str(encounter.id),
            "meta": {
                "profile": [
                    "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-encounter|1.0.0"
                ]
            },
            "status": "finished" if encounter.status != "OPEN" else "in-progress",
            "class": {"code": "AMB", "display": "Ambulatory"},
            "subject": {"reference": f"Patient/{person.id}"},
            "serviceProvider": {"reference": f"Organization/{facility_id}"},
        }

    providers = actor_provider_identity_resources(
        db, user_id=plan.created_by, facility_id=facility_id
    )
    role = next((r for r in providers if r.get("resourceType") == "PractitionerRole"), None)
    author = (
        {"reference": f"PractitionerRole/{role['id']}"}
        if role
        else {"reference": f"Organization/{facility_id}"}
    )

    created_at = plan.created_at
    if created_at is None:
        raise ClinicalCarePlanFhirError("CARE_PLAN_TIMESTAMP_REQUIRED")

    care_plan = {
        "resourceType": "CarePlan",
        "id": str(plan.id),
        "identifier": [{
            "use": "official",
            "system": "https://afyasync.health.ke/fhir/care-plans",
            "value": str(plan.id),
        }],
        "status": STATUS_MAP.get(plan.status, "active"),
        "intent": "plan",
        "title": plan.title,
        "subject": {"reference": f"Patient/{person.id}"},
        "created": _iso(created_at),
        "author": [author],
    }
    if plan.encounter_id is not None:
        care_plan["encounter"] = {"reference": f"Encounter/{plan.encounter_id}"}
    if plan.target_date is not None:
        care_plan["period"] = {
            "start": _iso(created_at),
            "end": datetime.combine(plan.target_date, time.min, tzinfo=timezone.utc).isoformat(),
        }
    else:
        care_plan["period"] = {"start": _iso(created_at)}

    for field, label in (
        ("goals", "Goals"),
        ("interventions", "Interventions"),
        ("clinical_notes", "Clinical notes"),
    ):
        narrative = _narrative(getattr(plan, field))
        if narrative:
            care_plan.setdefault("note", []).append(
                {"text": f"{label}: {narrative['text']['div'][5:-6]}"}
            )

    if plan.goals:
        care_plan["goal"] = [{"description": {"text": plan.goals}}]
    if plan.interventions:
        care_plan["activity"] = [{
            "detail": {
                "status": "completed" if plan.status == "COMPLETED" else "in-progress",
                "description": plan.interventions,
            }
        }]
    if plan.completed_at:
        care_plan["period"]["end"] = _iso(plan.completed_at)

    provenance_time = plan.updated_at or plan.completed_at or created_at
    provenance = {
        "resourceType": "Provenance",
        "id": f"clinical-care-plan-provenance-{plan.id}",
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"
            ]
        },
        "target": [{"reference": f"CarePlan/{plan.id}"}],
        "recorded": _iso(provenance_time),
        "agent": [{"type": {"text": "care plan author"}, "who": author}],
        "reason": [{"text": "Clinical care plan interoperability"}],
    }

    resources = [patient, facility, *providers]
    if encounter_resource:
        resources.append(encounter_resource)
    resources.extend([care_plan, provenance])

    bundle = {
        "resourceType": "Bundle",
        "id": f"clinical-care-plan-fhir-{plan.id}",
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
        raise ClinicalCarePlanFhirError(str(exc)) from exc

    record_audit(
        db,
        action="HIE_CLINICAL_CARE_PLAN_EXPORT",
        resource_type="CARE_PLAN",
        resource_id=str(plan.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=plan.patient_id,
        metadata={"status": plan.status},
        commit=False,
    )
    return bundle
