from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock

import app.facilities.service as facility_service
from app.facilities.service import Department, create_department


def test_create_department_audits_before_commit(monkeypatch) -> None:
    db = Mock()
    facility_id = uuid4()
    actor_user_id = uuid4()
    db.get.return_value = SimpleNamespace(id=facility_id)
    # First real use of the Department class is the duplicate-code lookup
    # (Department.facility_id / Department.code as query columns); it must
    # stay a real class here, not a stand-in, or that query breaks. Only the
    # *result* of the lookup (no existing department) is mocked.
    db.scalar.return_value = None
    audit_mock = Mock()

    monkeypatch.setattr(facility_service, "record_audit", audit_mock)

    result = create_department(
        db,
        facility_id,
        {"name": "Outpatient", "code": "OPD"},
        actor_user_id=actor_user_id,
    )

    assert isinstance(result, Department)
    assert result.facility_id == facility_id
    assert result.name == "Outpatient"
    assert result.code == "OPD"
    assert db.flush.call_count == 1
    assert db.commit.call_count == 1
    assert audit_mock.call_args.kwargs["commit"] is False
    assert audit_mock.call_args.kwargs["user_id"] == actor_user_id
    assert audit_mock.call_args.kwargs["facility_id"] == facility_id
