from uuid import uuid4

from app.hie.conformance import validate_kenya_core_resource


def test_phase187_medication_administration_required_fields():
    resource = {
        "resourceType": "MedicationAdministration",
        "id": str(uuid4()),
        "status": "completed",
        "medicationCodeableConcept": {"coding": [{"system": "https://example.org/medication", "code": "M1"}]},
        "subject": {"reference": "Patient/example"},
        "context": {"reference": "Encounter/example"},
        "effectiveDateTime": "2026-01-01T10:00:00+00:00",
        "performer": [{"actor": {"reference": "Practitioner/example"}}],
        "quantity": {"value": 1, "unit": "unit"},
    }
    assert resource["status"] in {"in-progress", "not-done", "on-hold", "completed", "entered-in-error", "stopped"}
    assert resource["subject"]["reference"].startswith("Patient/")
    assert resource["context"]["reference"].startswith("Encounter/")
    assert resource["performer"][0]["actor"]["reference"].startswith("Practitioner")
    assert validate_kenya_core_resource(resource) == []


def test_phase187_does_not_claim_unverified_kenya_profile():
    resource = {
        "resourceType": "MedicationAdministration",
        "id": "med-admin-example",
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/not-verified"]},
        "status": "completed",
        "subject": {"reference": "Patient/example"},
    }
    assert validate_kenya_core_resource(resource) == []
