from app.hie.conformance import validate_kenya_core_resource

PROFILE="https://fhir.dha.go.ke/kps/StructureDefinition/ke-kps-imaging-study"

def test_imaging_study_requires_core_fields():
    resource={"resourceType":"ImagingStudy","id":"i1","meta":{"profile":[PROFILE]},"status":"available","subject":{"reference":"Patient/p1"},"started":"2026-10-05T10:00:00+00:00","modality":[{"system":"http://dicom.nema.org/resources/ontology/DCM","code":"CT"}]}
    assert validate_kenya_core_resource(resource)==[]

def test_imaging_study_requires_modality():
    resource={"resourceType":"ImagingStudy","id":"i1","meta":{"profile":[PROFILE]},"status":"available","subject":{"reference":"Patient/p1"},"started":"2026-10-05T10:00:00+00:00"}
    assert "IMAGINGSTUDY_MODALITY_REQUIRED" in validate_kenya_core_resource(resource)
