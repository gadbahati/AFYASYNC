from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock

import app.facilities.service as facility_service
from app.facilities.service import create_department


def test_create_department_audits_before_commit(monkeypatch) -> None:
    db = Mock()
    facility_id = uuid4()
    actor_user_id = uuid4()
    department = SimpleNamespace(id=uuid4(), name="Outpatient", code="OPD")
    db.get.return_value = SimpleNamespace(id=facility_id)
    audit_mock = Mock()

    monkeypatch.setattr(facility_service, "Department", lambda **_: department)
    monkeypatch.setattr(facility_service, "record_audit", audit_mock)

    result = create_department(
        db,
        facility_id,
        {"name": "Outpatient", "code": "OPD"},
        actor_user_id=actor_user_id,
    )

    assert result is department
    assert db.flush.call_count == 1
    assert db.commit.call_count == 1
    assert audit_mock.call_args.kwargs["commit"] is False
    assert audit_mock.call_args.kwargs["user_id"] == actor_user_id
    assert audit_mock.call_args.kwargs["facility_id"] == facility_id
