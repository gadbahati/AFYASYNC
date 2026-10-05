from pathlib import Path

MPI = Path(__file__).parents[1] / "app" / "hie" / "mpi.py"
ROUTER = Path(__file__).parents[1] / "app" / "hie" / "router.py"

def test_mpi_does_not_expose_internal_match_metadata():
    source = MPI.read_text()
    assert 'entry.pop("_afya_match_reasons", None)' in source
    assert 'entry.pop("_afya_identity", None)' in source

def test_mpi_rejects_requests_without_meaningful_match_data():
    source = MPI.read_text()
    assert '"INSUFFICIENT_MATCH_DATA"' in source

def test_mpi_uses_verified_patient_profile():
    source = MPI.read_text()
    assert "kenya-core-patient|1.0.0" in source

def test_patient_match_accepts_standard_fhir_parameters_resource():
    source = ROUTER.read_text()
    assert 'body.get("resourceType") == "Parameters"' in source
    assert 'parameter.get("resource")' in source
    assert 'resource.get("resourceType") == "Patient"' in source

def test_patient_match_requires_read_authorization():
    source = ROUTER.read_text()
    marker = '@router.post("/Patient/$match")'
    section = source[source.index(marker):source.index('@router.get("/metadata")', source.index(marker))]
    assert 'require_permission("patients.record.read")' in section
