from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock

from sqlalchemy.exc import IntegrityError

import app.facilities.service as facility_service
from app.facilities.service import Department, create_department, create_facility


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


def test_create_facility_retries_facility_id_collision(monkeypatch) -> None:
    db = Mock()
    nested = Mock()
    nested.__enter__ = Mock(return_value=nested)
    nested.__exit__ = Mock(return_value=False)
    db.begin_nested.return_value = nested
    db.flush.side_effect = [
        IntegrityError("insert", {}, Exception("duplicate facility_id")),
        None,
    ]
    monkeypatch.setattr(
        facility_service,
        "_next_facility_id",
        Mock(side_effect=["FAC-000001", "FAC-000002"]),
    )
    audit_mock = Mock()
    monkeypatch.setattr(facility_service, "record_audit", audit_mock)

    result = create_facility(
        db,
        {"name": "General Hospital", "facility_type": "HOSPITAL"},
    )

    assert result.facility_id == "FAC-000002"
    assert db.begin_nested.call_count == 2
    assert db.flush.call_count == 2
    assert db.commit.call_count == 1
    assert db.refresh.call_count == 1
    assert audit_mock.call_count == 1
    assert audit_mock.call_args.kwargs["commit"] is False
