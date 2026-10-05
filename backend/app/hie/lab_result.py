"""FHIR Kenya Core representation of a verified laboratory result."""
from __future__ import annotations

from datetime import timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.hie.terminology_service import canonical_coding
from app.encounters.models import Encounter
from app.laboratory.models import LabOrder, LabOrderItem, LabResult, LabSample, LabTest
from app.patients.models import Person

KENYA_CORE_OBSERVATION_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-observation|1.0.0"
KENYA_CORE_DIAGNOSTIC_REPORT_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-diagnosticreport|1.0.0"
KENYA_CORE_SERVICEREQUEST_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-servicerequest|1.0.0"
KENYA_CORE_TASK_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-task|1.0.0"
KENYA_CORE_PROVENANCE_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"
DIAGNOSTIC_SECTION_SYSTEM = "http://terminology.hl7.org/CodeSystem/diagnostic-service-sections"
LAB_SECTION_CODE = "LAB"
class LabResultFhirError(ValueError):
    pass

def build_verified_lab_result_bundle(db: Session, *, result_id: UUID, facility_id: UUID) -> dict:
    result = db.get(LabResult, result_id)
    if result is None:
        raise LabResultFhirError("LAB_RESULT_NOT_FOUND")
    item = db.get(LabOrderItem, result.lab_order_item_id)
    order = db.get(LabOrder, item.lab_order_id) if item else None
    sample = db.get(LabSample, result.sample_id)
    test = db.get(LabTest, item.test_id) if item else None
    if not item or not order or not sample or not test:
        raise LabResultFhirError("LAB_RESULT_CONTEXT_INCOMPLETE")
    encounter = db.get(Encounter, order.encounter_id)
    person = db.get(Person, order.patient_id)
    if not encounter or encounter.facility_id != facility_id:
        raise LabResultFhirError("FACILITY_ACCESS_DENIED")
    if not person:
        raise LabResultFhirError("PATIENT_NOT_FOUND")
    if result.status != "VERIFIED":
        raise LabResultFhirError("LAB_RESULT_NOT_VERIFIED")
    coding = canonical_coding(db, "AFYASYNC:LAB_TEST", test.code, display=test.name)
    if not coding:
        raise LabResultFhirError("LAB_TEST_NOT_NATIONALLY_MAPPED")
    facility = _facility_organization_resource(db, facility_id)
    patient = _patient_resource(db, person)
    patient["meta"] = {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"]}
    performers = provider_identity_resources(db, staff_id=result.verified_by, facility_id=facility_id) if result.verified_by else []
    practitioner = next((r for r in performers if r.get("resourceType") == "Practitioner"), None)
    practitioner_role = next((r for r in performers if r.get("resourceType") == "PractitionerRole"), None)
    performer_ref = {"reference": f"PractitionerRole/{practitioner_role['id']}"} if practitioner_role else {"reference": f"Organization/{facility_id}"}
    effective = (result.verified_at or result.created_at).astimezone(timezone.utc).isoformat()
    observation = {
        "resourceType": "Observation", "id": f"lab-observation-{result.id}",
        "meta": {"profile": [KENYA_CORE_OBSERVATION_PROFILE]},
        "status": "final",
        "category": [{"coding": [{"system": DIAGNOSTIC_SECTION_SYSTEM, "code": LAB_SECTION_CODE, "display": "Laboratory"}], "text": "Laboratory"}],
        "code": {"coding": [coding], "text": test.name},
        "subject": {"reference": f"Patient/{person.id}"},
        "encounter": {"reference": f"Encounter/{encounter.id}"},
        "effectiveDateTime": effective,
        "performer": [performer_ref],
        "valueString": result.result,
    }
    if result.unit:
        observation["note"] = [{"text": f"Unit: {result.unit}"}]
    if result.reference_range:
        observation["referenceRange"] = [{"text": result.reference_range}]
    if result.comments:
        observation.setdefault("note", []).append({"text": result.comments})
    service_request = {
        "resourceType": "ServiceRequest", "id": f"lab-servicerequest-{order.id}-{item.id}",
        "meta": {"profile": [KENYA_CORE_SERVICEREQUEST_PROFILE]},
        "status": "completed", "intent": "order", "priority": {"URGENT": "urgent", "EMERGENCY": "stat"}.get(order.priority, "routine"),
        "subject": {"reference": f"Patient/{person.id}"}, "encounter": {"reference": f"Encounter/{encounter.id}"},
        "code": {"coding": [coding], "text": test.name}, "authoredOn": order.created_at.astimezone(timezone.utc).isoformat(),
        "requester": {"reference": f"Organization/{facility_id}"}, "performer": [performer_ref],
        "supportingInfo": [{"reference": f"Patient/{person.id}"}],
    }
    task_status = "completed" if item.status == "RESULT_VERIFIED" else "in-progress"
    task = {
        "resourceType": "Task", "id": f"lab-task-{item.id}",
        "meta": {"profile": [KENYA_CORE_TASK_PROFILE]}, "status": task_status, "intent": "order",
        "priority": {"URGENT": "urgent", "EMERGENCY": "stat"}.get(order.priority, "routine"),
        "code": {"coding": [coding], "text": "Laboratory order fulfilment"},
        "description": f"Laboratory test fulfilment: {test.name}",
        "focus": {"reference": f"ServiceRequest/{service_request['id']}"},
        "for": {"reference": f"Patient/{person.id}"}, "encounter": {"reference": f"Encounter/{encounter.id}"},
        "authoredOn": order.created_at.astimezone(timezone.utc).isoformat(), "owner": performer_ref,
    }
    if result.verified_at:
        task["executionPeriod"] = {"start": order.created_at.astimezone(timezone.utc).isoformat(), "end": effective}
    report = {
        "resourceType": "DiagnosticReport", "id": f"lab-report-{result.id}",
        "meta": {"profile": [KENYA_CORE_DIAGNOSTIC_REPORT_PROFILE]}, "status": "final",
        "category": [{"coding": [{"system": DIAGNOSTIC_SECTION_SYSTEM, "code": LAB_SECTION_CODE, "display": "Laboratory"}]}],
        "code": {"coding": [coding], "text": test.name},
        "subject": {"reference": f"Patient/{person.id}"}, "encounter": {"reference": f"Encounter/{encounter.id}"},
        "effectiveDateTime": effective, "issued": effective, "performer": [performer_ref],
        "basedOn": [{"reference": f"ServiceRequest/{service_request['id']}"}],
        "result": [{"reference": f"Observation/{observation['id']}"}],
    }
    provenance = {
        "resourceType": "Provenance", "id": f"lab-result-provenance-{result.id}",
        "meta": {"profile": [KENYA_CORE_PROVENANCE_PROFILE]},
        "target": [{"reference": f"Observation/{observation['id']}"}, {"reference": f"DiagnosticReport/{report['id']}"}],
        "recorded": effective, "agent": [{"type": {"text": "verifier"}, "who": performer_ref}],
        "reason": [{"text": "Verified laboratory result interoperability"}],
    }
    resources = [patient, facility, *performers, service_request, task, observation, report, provenance]
    bundle = {"resourceType": "Bundle", "id": f"lab-result-fhir-{result.id}", "type": "collection",
              "entry": [{"fullUrl": f"urn:uuid:{r['resourceType']}/{r['id']}", "resource": r} for r in resources]}
    try:
        assert_valid_bundle(bundle)
    except ValueError as exc:
        raise LabResultFhirError(str(exc)) from exc
    return bundle
