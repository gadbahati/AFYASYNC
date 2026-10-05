"""Kenya Core ServiceRequest generation for AfyaSync clinical orders."""
from __future__ import annotations

from datetime import timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.clinical.order_models import ClinicalOrder
from app.encounters.models import Encounter
from app.hie.provider_identity import actor_provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.hie.terminology_service import canonical_coding
from app.patients.models import Person

KENYA_CORE_SERVICEREQUEST_PROFILE = (
    "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-servicerequest|1.0.0"
)


class ServiceRequestError(ValueError):
    pass


def build_service_request(
    db: Session,
    *,
    order_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None,
) -> dict:
    order = db.get(ClinicalOrder, order_id)
    if order is None:
        raise ServiceRequestError("ORDER_NOT_FOUND")
    if order.facility_id != facility_id:
        raise ServiceRequestError("FACILITY_ACCESS_DENIED")
    if not order.code or not order.code_system:
        raise ServiceRequestError("ORDER_CODE_AND_SYSTEM_REQUIRED_FOR_FHIR")

    encounter = db.get(Encounter, order.encounter_id)
    if encounter is None or encounter.facility_id != facility_id:
        raise ServiceRequestError("ENCOUNTER_NOT_FOUND")
    person = db.get(Person, order.patient_id)
    if person is None:
        raise ServiceRequestError("PATIENT_NOT_FOUND")

    coding = canonical_coding(
        db,
        source_system=order.code_system,
        source_code=order.code,
        display=order.description,
    )
    if coding is None:
        raise ServiceRequestError("ORDER_CODE_NOT_NATIONALLY_MAPPED")

    provider_resources = actor_provider_identity_resources(
        db, user_id=actor_user_id, facility_id=facility_id
    )
    practitioner_role = next(
        (r for r in provider_resources if r.get("resourceType") == "PractitionerRole"),
        None,
    )

    authored = order.ordered_at
    if authored is None:
        raise ServiceRequestError("ORDER_AUTHORED_AT_REQUIRED")

    resource = {
        "resourceType": "ServiceRequest",
        "id": str(order.id),
        "meta": {"profile": [KENYA_CORE_SERVICEREQUEST_PROFILE]},
        "status": {
            "ORDERED": "active",
            "IN_PROGRESS": "active",
            "COMPLETED": "completed",
            "CANCELLED": "revoked",
        }.get(order.status, "active"),
        "intent": "order",
        "priority": {
            "ROUTINE": "routine",
            "URGENT": "urgent",
            "STAT": "stat",
        }.get(order.priority, "routine"),
        "subject": {"reference": f"Patient/{person.id}"},
        "encounter": {"reference": f"Encounter/{encounter.id}"},
        "code": {
            "coding": [coding],
            "text": order.description,
        },
        "authoredOn": authored.astimezone(timezone.utc).isoformat(),
        "requester": (
            {"reference": f"PractitionerRole/{practitioner_role['id']}"}
            if practitioner_role
            else {"reference": f"Organization/{facility_id}"}
        ),
    }
    if order.notes:
        resource["note"] = [{"text": order.notes}]
    return resource


def build_service_request_bundle(
    db: Session,
    *,
    order_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None,
) -> dict:
    order = db.get(ClinicalOrder, order_id)
    if order is None:
        raise ServiceRequestError("ORDER_NOT_FOUND")
    service_request = build_service_request(
        db, order_id=order_id, facility_id=facility_id, actor_user_id=actor_user_id
    )
    encounter = db.get(Encounter, order.encounter_id)
    person = db.get(Person, order.patient_id)
    if encounter is None or person is None:
        raise ServiceRequestError("CLINICAL_CONTEXT_NOT_FOUND")

    patient = _patient_resource(db, person)
    patient["meta"] = {
        "profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"]
    }
    organization = _facility_organization_resource(db, facility_id)
    resources = [patient, organization]
    provider_resources = actor_provider_identity_resources(
        db, user_id=actor_user_id, facility_id=facility_id
    )
    resources.extend(provider_resources)
    resources.append(service_request)

    entries = [
        {
            "fullUrl": f"urn:uuid:{resource['resourceType']}/{resource['id']}",
            "resource": resource,
        }
        for resource in resources
    ]
    return {
        "resourceType": "Bundle",
        "id": f"service-request-{order.id}",
        "type": "collection",
        "entry": entries,
    }
