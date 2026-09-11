from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import app.patients.service as patient_service
from app.patients.service import enroll_patient_in_facility, update_patient_facility_status


def test_enroll_patient_in_facility_creates_active_membership(monkeypatch) -> None:
    db = Mock()
    db.scalar.side_effect = [uuid4(), None]
    audit_mock = Mock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)

    patient_id = uuid4()
    facility_id = uuid4()
    actor_id = uuid4()

    result = enroll_patient_in_facility(db, patient_id, facility_id, actor_user_id=actor_id)

    assert result.patient_id == patient_id
    assert result.facility_id == facility_id
    assert result.status == "ACTIVE"
    assert db.add.call_count == 1
    assert db.flush.call_count == 1
    assert db.commit.call_count == 1
    assert audit_mock.call_args.kwargs["action"] == "ENROLL_PATIENT_FACILITY"
    assert audit_mock.call_args.kwargs["commit"] is False
    assert audit_mock.call_args.kwargs["facility_id"] == facility_id
    assert audit_mock.call_args.kwargs["patient_id"] == patient_id
    assert audit_mock.call_args.kwargs["user_id"] == actor_id


def test_enroll_patient_in_facility_reactivates_inactive_membership(monkeypatch) -> None:
    db = Mock()
    membership = SimpleNamespace(id=uuid4(), patient_id=uuid4(), facility_id=uuid4(), status="INACTIVE")
    db.scalar.side_effect = [membership, membership]
    audit_mock = Mock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)

    result = enroll_patient_in_facility(db, membership.patient_id, membership.facility_id, actor_user_id=uuid4())

    assert result is membership
    assert membership.status == "ACTIVE"
    db.add.assert_not_called()
    db.flush.assert_called_once()
    db.commit.assert_called_once()
    assert audit_mock.call_args.kwargs["action"] == "REACTIVATE_PATIENT_FACILITY"
    assert audit_mock.call_args.kwargs["commit"] is False


def test_enroll_patient_in_facility_rejects_existing_active_membership(monkeypatch) -> None:
    db = Mock()
    membership = SimpleNamespace(id=uuid4(), status="ACTIVE")
    db.scalar.side_effect = [uuid4(), membership]
    audit_mock = Mock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)

    try:
        enroll_patient_in_facility(db, uuid4(), uuid4(), actor_user_id=uuid4())
    except ValueError as exc:
        assert str(exc) == "PATIENT_ALREADY_ENROLLED"
    else:
        raise AssertionError("Expected duplicate enrollment rejection")

    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    audit_mock.assert_not_called()


def test_enroll_patient_in_facility_rejects_unknown_patient(monkeypatch) -> None:
    db = Mock()
    db.scalar.return_value = None
    audit_mock = Mock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)

    try:
        enroll_patient_in_facility(db, uuid4(), uuid4(), actor_user_id=uuid4())
    except ValueError as exc:
        assert str(exc) == "PATIENT_NOT_FOUND"
    else:
        raise AssertionError("Expected unknown patient rejection")

    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    audit_mock.assert_not_called()


def test_update_patient_facility_status_deactivates_membership(monkeypatch) -> None:
    db = Mock()
    membership = SimpleNamespace(id=uuid4(), patient_id=uuid4(), facility_id=uuid4(), status="ACTIVE")
    db.scalar.return_value = membership
    audit_mock = Mock()
    monkeypatch.setattr(patient_service, "record_audit", audit_mock)

    result = update_patient_facility_status(db, membership.patient_id, membership.facility_id, "INACTIVE", actor_user_id=uuid4())

    assert result is membership
    assert membership.status == "INACTIVE"
    db.flush.assert_called_once()
    db.commit.assert_called_once()
    assert audit_mock.call_args.kwargs["action"] == "UPDATE_PATIENT_FACILITY_STATUS"
    assert audit_mock.call_args.kwargs["metadata"] == {"previous_status": "ACTIVE", "new_status": "INACTIVE"}
    assert audit_mock.call_args.kwargs["commit"] is False


def test_update_patient_facility_status_rejects_unchanged_status(monkeypatch) -> None:
    db = Mock()
    membership = SimpleNamespace(id=uuid4(), patient_id=uuid4(), facility_id=uuid4(), status="ACTIVE")
    db.scalar.return_value = membership
    audit_mock = Mock()
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
    db = Mock()
    audit_mock = Mock()
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
