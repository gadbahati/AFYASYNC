from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

import app.patients.service as patient_service
from app.patients.service import (
    enroll_patient_in_facility,
    get_patient_facility_enrollments,
    list_patients_for_facility,
    update_patient_facility_status,
)


def _configure_nested_transaction(db: MagicMock) -> None:
    """Make the mocked savepoint behave like SQLAlchemy's context manager."""
    db.begin_nested.return_value.__enter__.return_value = db.begin_nested.return_value
    db.begin_nested.return_value.__exit__.return_value = False


def test_enroll_patient_in_facility_creates_active_membership(monkeypatch) -> None:
    db = MagicMock()
    _configure_nested_transaction(db)
    db.scalar.side_effect = [uuid4(), None]
    audit_mock = MagicMock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)
    patient_id, facility_id, actor_id = uuid4(), uuid4(), uuid4()
    result = enroll_patient_in_facility(db, patient_id, facility_id, actor_user_id=actor_id)
    assert result.patient_id == patient_id
    assert result.facility_id == facility_id
    assert result.status == "ACTIVE"
    assert db.add.call_count == 1
    assert db.flush.call_count == 1
    assert db.commit.call_count == 1
    assert audit_mock.call_args.kwargs["action"] == "ENROLL_PATIENT_FACILITY"
    assert audit_mock.call_args.kwargs["commit"] is False


def test_enroll_patient_in_facility_reactivates_inactive_membership(monkeypatch) -> None:
    db = MagicMock()
    membership = SimpleNamespace(id=uuid4(), patient_id=uuid4(), facility_id=uuid4(), status="INACTIVE")
    db.scalar.side_effect = [membership, membership]
    audit_mock = MagicMock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)
    result = enroll_patient_in_facility(db, membership.patient_id, membership.facility_id, actor_user_id=uuid4())
    assert result is membership
    assert membership.status == "ACTIVE"
    db.add.assert_not_called()
    db.flush.assert_called_once()
    db.commit.assert_called_once()
    assert audit_mock.call_args.kwargs["action"] == "REACTIVATE_PATIENT_FACILITY"


def test_enroll_patient_in_facility_rejects_existing_active_membership(monkeypatch) -> None:
    db = MagicMock()
    membership = SimpleNamespace(id=uuid4(), status="ACTIVE")
    db.scalar.side_effect = [uuid4(), membership]
    audit_mock = MagicMock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)
    try:
        enroll_patient_in_facility(db, uuid4(), uuid4(), actor_user_id=uuid4())
    except ValueError as exc:
        assert str(exc) == "PATIENT_ALREADY_ENROLLED"
    else:
        raise AssertionError("Expected duplicate enrollment rejection")
    db.add.assert_not_called()
    db.commit.assert_not_called()
    audit_mock.assert_not_called()


def test_enroll_patient_in_facility_rejects_unknown_patient(monkeypatch) -> None:
    db = MagicMock()
    db.scalar.return_value = None
    audit_mock = MagicMock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)
    try:
        enroll_patient_in_facility(db, uuid4(), uuid4(), actor_user_id=uuid4())
    except ValueError as exc:
        assert str(exc) == "PATIENT_NOT_FOUND"
    else:
        raise AssertionError("Expected unknown patient rejection")
    db.add.assert_not_called()
    db.commit.assert_not_called()
    audit_mock.assert_not_called()


def test_enroll_patient_in_facility_handles_concurrent_duplicate(monkeypatch) -> None:
    db = MagicMock()
    _configure_nested_transaction(db)
    patient_id, facility_id = uuid4(), uuid4()
    membership = SimpleNamespace(id=uuid4(), patient_id=patient_id, facility_id=facility_id, status="ACTIVE")
    db.scalar.side_effect = [uuid4(), None, membership]
    db.flush.side_effect = [IntegrityError("INSERT", {}, Exception("duplicate key"))]
    audit_mock = MagicMock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)

    try:
        enroll_patient_in_facility(db, patient_id, facility_id, actor_user_id=uuid4())
    except ValueError as exc:
        assert str(exc) == "PATIENT_ALREADY_ENROLLED"
    else:
        raise AssertionError("Expected concurrent duplicate enrollment rejection")

    db.begin_nested.assert_called_once()
    db.commit.assert_not_called()
    audit_mock.assert_not_called()


def test_update_patient_facility_status_deactivates_membership(monkeypatch) -> None:
    db = MagicMock()
    membership = SimpleNamespace(id=uuid4(), patient_id=uuid4(), facility_id=uuid4(), status="ACTIVE")
    db.scalar.return_value = membership
    audit_mock = MagicMock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)
    result = update_patient_facility_status(db, membership.patient_id, membership.facility_id, "INACTIVE", actor_user_id=uuid4())
    assert result is membership
    assert membership.status == "INACTIVE"
    db.flush.assert_called_once()
    db.commit.assert_called_once()
    assert audit_mock.call_args.kwargs["action"] == "UPDATE_PATIENT_FACILITY_STATUS"


def test_update_patient_facility_status_rejects_unchanged_status(monkeypatch) -> None:
    db = MagicMock()
    membership = SimpleNamespace(id=uuid4(), patient_id=uuid4(), facility_id=uuid4(), status="ACTIVE")
    db.scalar.return_value = membership
    audit_mock = MagicMock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)
    try:
        update_patient_facility_status(db, membership.patient_id, membership.facility_id, "ACTIVE", actor_user_id=uuid4())
    except ValueError as exc:
        assert str(exc) == "PATIENT_FACILITY_STATUS_UNCHANGED"
    else:
        raise AssertionError("Expected unchanged status rejection")
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    audit_mock.assert_not_called()


def test_update_patient_facility_status_rejects_invalid_status(monkeypatch) -> None:
    db = MagicMock()
    audit_mock = MagicMock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)
    try:
        update_patient_facility_status(db, uuid4(), uuid4(), "DECEASED", actor_user_id=uuid4())
    except ValueError as exc:
        assert str(exc) == "INVALID_PATIENT_FACILITY_STATUS"
    else:
        raise AssertionError("Expected invalid status rejection")
    db.scalar.assert_not_called()
    db.commit.assert_not_called()
    audit_mock.assert_not_called()


def test_get_patient_facility_enrollments_is_scoped_to_requested_facility() -> None:
    db = MagicMock()
    patient_id, facility_id = uuid4(), uuid4()
    memberships = [SimpleNamespace(id=uuid4(), facility_id=facility_id, status="ACTIVE")]
    db.scalars.return_value.all.return_value = memberships
    result = get_patient_facility_enrollments(db, patient_id, facility_id)
    assert result == memberships
    db.scalars.assert_called_once()
    statement = db.scalars.call_args.args[0]
    compiled = statement.compile()
    assert "patient_facilities.facility_id" in str(compiled)
    assert facility_id in compiled.params.values()


def test_list_patients_for_facility_returns_paginated_rows_and_total() -> None:
    db = MagicMock()
    facility_id = uuid4()
    person = SimpleNamespace(id=uuid4(), first_name="Jane", last_name="Doe")
    identity = SimpleNamespace(person_id=person.id, afya_id="AF-00000001")
    db.scalar.return_value = 1
    db.execute.return_value.all.return_value = [(person, identity)]
    items, total = list_patients_for_facility(db, facility_id, limit=25, offset=10)
    assert items == [(person, identity)]
    assert total == 1
    db.scalar.assert_called_once()
    db.execute.assert_called_once()
    statement = db.execute.call_args.args[0]
    compiled = statement.compile()
    assert "patient_facilities.facility_id" in str(compiled)
    assert facility_id in compiled.params.values()
    status_params = {k: v for k, v in compiled.params.items() if k.startswith("status_")}
    assert "ACTIVE" in status_params.values()
