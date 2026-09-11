from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock

from app.patients.service import create_patient


def test_create_patient_audits_before_commit(monkeypatch) -> None:
    db = Mock()
    db.scalar.side_effect = [None, 42]
    person = SimpleNamespace(id=uuid4(), afya_identity=None)
    identity = SimpleNamespace(afya_id="AF-00000042")

    monkeypatch.setattr("app.patients.service.Person", lambda **_: person)
    monkeypatch.setattr("app.patients.service.AfyaIdentity", lambda **_: identity)
    monkeypatch.setattr("app.patients.service.record_audit", Mock())
    monkeypatch.setattr(
        "app.patients.service.PatientCreate.model_dump",
        lambda self: {"first_name": "Test", "last_name": "Patient"},
    )

    payload = SimpleNamespace(
        phone=None,
        first_name="Test",
        last_name="Patient",
        model_dump=lambda: {"first_name": "Test", "last_name": "Patient"},
    )

    result = create_patient(db, payload, actor_user_id=uuid4(), facility_id=uuid4())

    assert result is person
    assert db.flush.call_count == 2
    assert db.commit.call_count == 1
    audit = monkeypatch
    audit_mock = __import__("app.patients.service", fromlist=["record_audit"]).record_audit
    assert audit_mock.call_args.kwargs["commit"] is False
    assert db.flush.call_args_list[1][0] == ()
    assert db.commit.call_count == 1
