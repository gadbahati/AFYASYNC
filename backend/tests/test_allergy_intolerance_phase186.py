from uuid import uuid4

from app.hie.conformance import validate_kenya_core_resource


def test_phase186_allergy_intolerance_required_fields():
    resource={
        "resourceType":"AllergyIntolerance",
        "id":f"allergy-{uuid4()}",
        "clinicalStatus":{"coding":[{"system":"http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical","code":"active"}]},
        "verificationStatus":{"coding":[{"system":"http://terminology.hl7.org/CodeSystem/allergyintolerance-verification","code":"confirmed"}]},
        "code":{"coding":[{"system":"https://example.invalid/verified-allergy","code":"verified-code"}]},
        "patient":{"reference":"Patient/example"},
    }
    assert resource["patient"]["reference"].startswith("Patient/")
    assert validate_kenya_core_resource(resource)==[]


def test_phase186_does_not_claim_unverified_kenya_profile():
    resource={
        "resourceType":"AllergyIntolerance",
        "id":"allergy-example",
        "meta":{"profile":["https://fhir.dha.go.ke/core/StructureDefinition/not-verified"]},
        "patient":{"reference":"Patient/example"},
    }
    assert validate_kenya_core_resource(resource)==[]
