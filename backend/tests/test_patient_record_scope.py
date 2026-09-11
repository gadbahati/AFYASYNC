from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

import app.patients.service as patient_service


def test_get_patient_for_facility_uses_patient_facility_scope() -> None:
    db = Mock()
    patient = SimpleNamespace(id=uuid4())
    db.scalar.return_value = patient
    facility_id = uuid4()

    result = patient_service.get_patient_for_facility(db, patient.id, facility_id)

    assert result is patient
    db.scalar.assert_called_once()


def test_create_patient_requires_facility_context() -> None:
    db = Mock()
    payload = SimpleNamespace(phone=None)

    with pytest.raises(ValueError, match="FACILITY_CONTEXT_REQUIRED"):
        patient_service.create_patient(db, payload, actor_user_id=uuid4(), facility_id=None)

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_create_patient_links_patient_to_facility(monkeypatch) -> None:
    db = Mock()
    db.scalar.return_value = 7
    person = SimpleNamespace(id=uuid4(), afya_identity=None)
    identity = SimpleNamespace(afya_id="AF-00000007")
    audit_mock = Mock()
    link = SimpleNamespace(patient_id=person.id, facility_id=uuid4())

    monkeypatch.setattr(patient_service, "Person", lambda **_: person)
    monkeypatch.setattr(patient_service, "AfyaIdentity", lambda **_: identity)
    monkeypatch.setattr(patient_service, "PatientFacility", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)
    payload = SimpleNamespace(
        phone=None,
        model_dump=lambda: {"first_name": "Test", "last_name": "Patient"},
    )

    result = patient_service.create_patient(
        db, payload, actor_user_id=uuid4(), facility_id=link.facility_id
    )

    assert result is person
    assert db.add.call_count == 3
    assert db.flush.call_count == 3
    assert db.commit.call_count == 1
    added_link = db.add.call_args_list[2].args[0]
    assert added_link.patient_id == person.id
    assert added_link.facility_id == link.facility_id
    assert audit_mock.call_args.kwargs["facility_id"] == link.facility_id
    assert audit_mock.call_args.kwargs["commit"] is False
