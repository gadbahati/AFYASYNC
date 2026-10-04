from uuid import uuid4

from app.hie.import_models import HieImportedResource
from app.hie.service import (
    _bundle_purpose_of_use,
    _inbound_consent_allows_sensitive,
    _parse_effective_at,
    _resource_code_and_text,
)


def test_hie_import_model_is_registered():
    assert HieImportedResource.__tablename__ == "hie_imported_resources"
    assert "uq_hie_imported_resource_remote" in {
        constraint.name for constraint in HieImportedResource.__table__.constraints
    }


def test_inbound_purpose_and_effective_date_are_normalized():
    payload = {
        "meta": {
            "tag": [
                {
                    "system": "https://afyasync.health.ke/purpose-of-use",
                    "code": "TREATMENT",
                }
            ]
        }
    }
    assert _bundle_purpose_of_use(payload) == "TREATMENT"
    effective = _parse_effective_at({"effectiveDateTime": "2026-10-04T10:20:00Z"})
    assert effective is not None
    assert effective.isoformat() == "2026-10-04T10:20:00+00:00"


def test_inbound_resource_normalization_extracts_code_and_text():
    code, text = _resource_code_and_text(
        {
            "resourceType": "Condition",
            "code": {
                "coding": [{"system": "http://id.who.int/icd/release/11-mms", "code": "1A00"}],
                "text": "Example condition",
            },
        }
    )
    assert code == "1A00"
    assert text == "Example condition"


def test_sensitive_import_requires_matching_patient_consent():
    patient_id = uuid4()
    permitted = {
        "entry": [
            {
                "resource": {
                    "resourceType": "Consent",
                    "patient": {"reference": f"Patient/{patient_id}"},
                    "provision": {
                        "type": "permit",
                        "purpose": [{"code": "TREATMENT"}],
                    },
                }
            }
        ]
    }
    denied = {
        "entry": [
            {
                "resource": {
                    "resourceType": "Consent",
                    "patient": {"reference": f"Patient/{uuid4()}"},
                    "provision": {
                        "type": "permit",
                        "purpose": [{"code": "TREATMENT"}],
                    },
                }
            }
        ]
    }
    assert _inbound_consent_allows_sensitive(permitted, patient_id, "TREATMENT")
    assert not _inbound_consent_allows_sensitive(denied, patient_id, "TREATMENT")
