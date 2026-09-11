from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock

import app.patients.service as patient_service
from app.patients.service import update_patient


def test_update_patient_is_atomic_and_audited(monkeypatch) -> None:
    db = Mock()
    db.scalar.return_value = None
    audit_mock = Mock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)

    patient = SimpleNamespace(id=uuid4(), first_name="Old", last_name="Name", phone="0700000000")
    payload = SimpleNamespace(model_dump=lambda **_: {"first_name": "New", "phone": "0711111111"})
    actor = uuid4()
    facility = uuid4()

    result = update_patient(db, patient, payload, actor_user_id=actor, facility_id=facility)

    assert result is patient
    assert patient.first_name == "New"
    assert patient.phone == "0711111111"
    assert db.flush.call_count == 1
    assert db.commit.call_count == 1
    assert audit_mock.call_args.kwargs["commit"] is False
    assert audit_mock.call_args.kwargs["user_id"] == actor
    assert audit_mock.call_args.kwargs["facility_id"] == facility
    assert audit_mock.call_args.kwargs["patient_id"] == patient.id
    assert audit_mock.call_args.kwargs["metadata"]["changed_fields"] == ["first_name", "phone"]


def test_update_patient_rejects_duplicate_phone(monkeypatch) -> None:
    db = Mock()
    db.scalar.return_value = SimpleNamespace(id=uuid4())
    patient = SimpleNamespace(id=uuid4(), first_name="Old", last_name="Name", phone="0700000000")
    payload = SimpleNamespace(model_dump=lambda **_: {"phone": "0711111111"})

    try:
        update_patient(db, patient, payload, actor_user_id=uuid4(), facility_id=uuid4())
    except ValueError as exc:
        assert str(exc) == "DUPLICATE_PHONE"
    else:
        raise AssertionError("Expected duplicate phone rejection")

    db.commit.assert_not_called()
