"""FHIR Kenya Core projection for completed clinical procedures."""
from __future__ import annotations
from datetime import timezone
from uuid import UUID
from sqlalchemy.orm import Session
from app.clinical.models import Procedure
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import actor_provider_identity_resources, provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.hie.terminology_service import canonical_coding
from app.patients.models import Person

KENYA_CORE_PROCEDURE_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-procedure|1.0.0"
KENYA_CORE_PROVENANCE_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"

class ProcedureFhirError(ValueError):
    pass

def build_procedure_bundle(db: Session, *, procedure_id: UUID, facility_id: UUID, actor_user_id: UUID | None) -> dict:
    procedure = db.get(Procedure, procedure_id)
    if procedure is None:
        raise ProcedureFhirError("PROCEDURE_NOT_FOUND")
    encounter = db.get(Encounter, procedure.encounter_id)
    if encounter is None or encounter.facility_id != facility_id:
        raise ProcedureFhirError("FACILITY_ACCESS_DENIED")
    person = db.get(Person, encounter.patient_id)
    if person is None:
        raise ProcedureFhirError("PATIENT_NOT_FOUND")
    if not procedure.code:
        raise ProcedureFhirError("PROCEDURE_CODE_REQUIRED")
    coding = canonical_coding(db, "AFYASYNC:PROCEDURE", procedure.code, display=procedure.name)
    if not coding:
        raise ProcedureFhirError("PROCEDURE_NOT_NATIONALLY_MAPPED")
    patient = _patient_resource(db, person)
    patient["meta"] = {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"]}
    facility = _facility_organization_resource(db, facility_id)
    providers = []
    if procedure.performed_by:
        providers = provider_identity_resources(db, facility_id=facility_id, staff_id=procedure.performed_by)
    else:
        providers = actor_provider_identity_resources(db, user_id=actor_user_id, facility_id=facility_id)
    role = next((r for r in providers if r.get("resourceType") == "PractitionerRole"), None)
    performer = {"actor": {"reference": f"PractitionerRole/{role['id']}"}} if role else {"actor": {"reference": f"Organization/{facility_id}"}}
    performed = procedure.performed_at.astimezone(timezone.utc).isoformat()
    resource = {
        "resourceType": "Procedure", "id": str(procedure.id),
        "meta": {"profile": [KENYA_CORE_PROCEDURE_PROFILE]},
        "status": "completed", "code": {"coding": [coding], "text": procedure.name},
        "subject": {"reference": f"Patient/{person.id}"},
        "encounter": {"reference": f"Encounter/{encounter.id}"},
        "performedDateTime": performed, "performer": [performer],
    }
    if procedure.notes:
        resource["note"] = [{"text": procedure.notes}]
    provenance = {
        "resourceType": "Provenance", "id": f"procedure-provenance-{procedure.id}",
        "meta": {"profile": [KENYA_CORE_PROVENANCE_PROFILE]},
        "target": [{"reference": f"Procedure/{procedure.id}"}],
        "recorded": performed,
        "agent": [{"type": {"text": "performer"}, "who": performer["actor"]}],
        "reason": [{"text": "Clinical procedure interoperability"}],
    }
    resources=[patient,facility,*providers,resource,provenance]
    bundle={"resourceType":"Bundle","id":f"procedure-fhir-{procedure.id}","type":"collection",
            "entry":[{"fullUrl":f"urn:uuid:{r['resourceType']}/{r['id']}","resource":r} for r in resources]}
    try: assert_valid_bundle(bundle)
    except ValueError as exc: raise ProcedureFhirError(str(exc)) from exc
    return bundle
