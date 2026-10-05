from app.hie.conformance import validate_kenya_core_resource

def test_kps_imaging_study_conformance():
    r={"resourceType":"ImagingStudy","id":"i1","meta":{"profile":["https://fhir.dha.go.ke/kps/StructureDefinition/ke-kps-imaging-study"]},
       "status":"available","subject":{"reference":"Patient/p1"},"started":"2026-10-05T10:00:00+00:00",
       "modality":[{"system":"http://dicom.nema.org/resources/ontology/DCM","code":"CT","display":"Computed Tomography"}]}
    assert validate_kenya_core_resource(r)==[]

def test_kps_diagnostic_report_accepts_imaging_study():
    r={"resourceType":"DiagnosticReport","id":"d1","meta":{"profile":["https://fhir.dha.go.ke/kps/StructureDefinition/ke-kps-diagnostic-report"]},
       "status":"final","code":{"text":"CT study"},"subject":{"reference":"Patient/p1"},"encounter":{"reference":"Encounter/e1"},
       "effectiveDateTime":"2026-10-05T10:00:00+00:00","issued":"2026-10-05T10:00:00+00:00",
       "performer":[{"reference":"Organization/o1"}],"imagingStudy":[{"reference":"ImagingStudy/i1"}]}
    assert validate_kenya_core_resource(r)==[]

def test_imaging_study_requires_modality():
    r={"resourceType":"ImagingStudy","id":"i1","meta":{"profile":["https://fhir.dha.go.ke/kps/StructureDefinition/ke-kps-imaging-study"]},
       "status":"available","subject":{"reference":"Patient/p1"},"started":"2026-10-05T10:00:00+00:00"}
    assert "IMAGINGSTUDY_MODALITY_REQUIRED" in validate_kenya_core_resource(r)
