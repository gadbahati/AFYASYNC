from app.hie.conformance import validate_kenya_core_resource

def test_diagnostic_report_requires_verified_result_fields():
    report = {
        "resourceType": "DiagnosticReport", "id": "dr1",
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-diagnosticreport|1.0.0"]},
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/diagnostic-service-sections", "code": "LAB"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "1234-5"}]},
        "subject": {"reference": "Patient/p1"}, "encounter": {"reference": "Encounter/e1"},
        "effectiveDateTime": "2026-10-05T10:00:00+00:00", "issued": "2026-10-05T10:00:00+00:00",
        "performer": [{"reference": "Organization/o1"}],
        "result": [{"reference": "Observation/o1"}],
    }
    assert validate_kenya_core_resource(report) == []

def test_observation_requires_effective_time():
    observation = {
        "resourceType": "Observation", "id": "o1",
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-observation|1.0.0"]},
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/diagnostic-service-sections", "code": "LAB"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "1234-5"}]},
        "subject": {"reference": "Patient/p1"},
    }
    assert "OBSERVATION_EFFECTIVEDATETIME_REQUIRED" in validate_kenya_core_resource(observation)
