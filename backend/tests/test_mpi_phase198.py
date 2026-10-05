from uuid import uuid4

from app.hie.conformance import validate_bundle


def test_phase198_mpi_match_searchset_conforms_without_forcing_patient():
    bundle = {
        "resourceType": "Bundle",
        "id": str(uuid4()),
        "type": "searchset",
        "total": 0,
        "entry": [],
        "link": [{"relation": "self", "url": "Patient/$match"}],
    }
    assert validate_bundle(bundle, require_patient=False, require_provenance=False) == []


def test_phase198_patient_match_uses_verified_kenya_patient_profile():
    pid = str(uuid4())
    bundle = {
        "resourceType": "Bundle",
        "id": str(uuid4()),
        "type": "searchset",
        "total": 1,
        "entry": [{
            "fullUrl": f"urn:uuid:Patient/{pid}",
            "resource": {
                "resourceType": "Patient",
                "id": pid,
                "meta": {"profile": [
                    "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"
                ]},
                "name": [{"text": "Example Patient"}],
            },
            "search": {"mode": "match", "score": 1.0},
        }],
    }
    assert validate_bundle(bundle, require_patient=False, require_provenance=False) == []
