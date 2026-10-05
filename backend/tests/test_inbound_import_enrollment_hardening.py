from pathlib import Path
P=Path(__file__).parents[1]/"app"/"hie"/"service.py"
s=P.read_text()

def test_inbound_import_requires_active_patient_enrollment():
    marker='    _require_enrollment(db, row.patient_id, facility_id)'
    assert marker in s
    assert 'PATIENT_NOT_IN_FACILITY' in s

def test_inbound_import_remains_facility_scoped():
    assert 'row.facility_id != facility_id' in s
    assert 'HieImportedResource.facility_id == facility_id' in s
