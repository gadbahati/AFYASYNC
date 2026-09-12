from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock

import app.patients.service as patient_service
from app.patients.service import create_patient


def test_create_patient_audits_before_commit(monkeypatch) -> None:
    db = Mock()
    db.scalar.side_effect = [None, 42]
    person = SimpleNamespace(id=uuid4(), afya_identity=None)
    identity = SimpleNamespace(afya_id="AF-00000042")
    audit_mock = Mock()

    monkeypatch.setattr(patient_service, "Person", lambda **_: person)
    monkeypatch.setattr(patient_service, "AfyaIdentity", lambda **_: identity)
    monkeypatch.setattr(patient_service, "PatientFacility", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)

    payload = SimpleNamespace(
        national_id_number="87654321",
        phone=None,
        first_name="Test",
        last_name="Patient",
        model_dump=lambda: {"first_name": "Test", "last_name": "Patient"},
    )

    actor_user_id = uuid4()
    facility_id = uuid4()
    result = create_patient(db, payload, actor_user_id=actor_user_id, facility_id=facility_id)

    assert result is person
    assert db.flush.call_count == 3
    assert db.commit.call_count == 1
    assert audit_mock.call_args.kwargs["commit"] is False
    assert audit_mock.call_args.kwargs["user_id"] == actor_user_id
    assert audit_mock.call_args.kwargs["facility_id"] == facility_id
    assert audit_mock.call_args.kwargs["patient_id"] == person.id
