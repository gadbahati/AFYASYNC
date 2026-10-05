from app.hie.conformance import validate_kenya_core_resource

PROFILE="https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-procedure|1.0.0"

def test_procedure_conformance():
    resource={
        "resourceType":"Procedure","id":"p1","meta":{"profile":[PROFILE]},
        "status":"completed","code":{"coding":[{"system":"https://example.test/procedure","code":"X"}]},
        "subject":{"reference":"Patient/p1"},"performedDateTime":"2026-10-05T10:00:00+00:00",
        "performer":[{"actor":{"reference":"Organization/o1"}}],
    }
    assert validate_kenya_core_resource(resource)==[]

def test_procedure_requires_code():
    resource={
        "resourceType":"Procedure","id":"p1","meta":{"profile":[PROFILE]},
        "status":"completed","subject":{"reference":"Patient/p1"},
        "performedDateTime":"2026-10-05T10:00:00+00:00",
        "performer":[{"actor":{"reference":"Organization/o1"}}],
    }
    assert "PROCEDURE_CODE_REQUIRED" in validate_kenya_core_resource(resource)
