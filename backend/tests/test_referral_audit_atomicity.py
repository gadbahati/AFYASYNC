from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.referrals.service import (
    create_referral,
    create_transfer,
    update_referral_status,
    update_transfer_status,
)


def _flush_before_single_commit(db) -> None:
    flush_index = next(i for i, call in enumerate(db.method_calls) if call[0] == "flush")
    commit_index = next(i for i, call in enumerate(db.method_calls) if call[0] == "commit")
    assert flush_index < commit_index
    assert sum(1 for call in db.method_calls if call[0] == "commit") == 1


def _single_commit(db) -> None:
    assert sum(1 for call in db.method_calls if call[0] == "commit") == 1


def test_create_referral_audits_before_single_commit() -> None:
    facility_id = uuid4()
    staff_id = uuid4()
    encounter_id = uuid4()
    destination_id = uuid4()
    encounter = MagicMock(facility_id=facility_id, status="OPEN", patient_id=uuid4(), id=encounter_id)
    staff = MagicMock(facility_id=facility_id, status="ACTIVE")
    destination = MagicMock(id=destination_id, status="ACTIVE")
    db = MagicMock()
    db.get.side_effect = [encounter, staff, destination]
    referral = MagicMock(id=uuid4(), patient_id=encounter.patient_id, status="CREATED", referral_id="REF-TEST")

    with patch("app.referrals.service.Referral", return_value=referral), \
         patch("app.referrals.service.notify_patient_event") as notify, \
         patch("app.referrals.service.record_audit") as audit:
        payload = {
            "encounter_id": encounter_id,
            "destination_facility_id": destination_id,
            "reason": "Needs specialist",
        }
        result = create_referral(db, facility_id, staff_id, payload, actor_user_id=uuid4())

    assert result is referral
    notify.assert_called_once()
    assert notify.call_args.kwargs["commit"] is False
    audit.assert_called_once()
    assert audit.call_args.kwargs["commit"] is False
    _flush_before_single_commit(db)


def test_update_referral_status_audits_before_single_commit() -> None:
    facility_id = uuid4()
    referral_id = uuid4()
    referral = MagicMock(id=referral_id, source_facility_id=facility_id, destination_facility_id=uuid4(), status="CREATED", patient_id=uuid4())
    db = MagicMock()
    db.get.return_value = referral

    with patch("app.referrals.service.notify_patient_event") as notify, \
         patch("app.referrals.service.record_audit") as audit:
        result = update_referral_status(db, facility_id, referral_id, "SENT", actor_user_id=uuid4())

    assert result is referral
    assert referral.status == "SENT"
    notify.assert_called_once()
    assert notify.call_args.kwargs["commit"] is False
    audit.assert_called_once()
    assert audit.call_args.kwargs["commit"] is False
    _single_commit(db)


def test_create_transfer_audits_before_single_commit() -> None:
    facility_id = uuid4()
    staff_id = uuid4()
    encounter_id = uuid4()
    destination_id = uuid4()
    encounter = MagicMock(facility_id=facility_id, status="OPEN", patient_id=uuid4(), id=encounter_id)
    staff = MagicMock(facility_id=facility_id, status="ACTIVE")
    destination = MagicMock(id=destination_id, status="ACTIVE")
    db = MagicMock()
    db.get.side_effect = [encounter, staff, destination]
    transfer = MagicMock(id=uuid4(), patient_id=encounter.patient_id, status="REQUESTED", transfer_id="TRF-TEST")

    with patch("app.referrals.service.Transfer", return_value=transfer), \
         patch("app.referrals.service.notify_patient_event") as notify, \
         patch("app.referrals.service.record_audit") as audit:
        payload = {
            "encounter_id": encounter_id,
            "destination_facility_id": destination_id,
            "reason": "Needs ICU bed",
        }
        result = create_transfer(db, facility_id, staff_id, payload, actor_user_id=uuid4())

    assert result is transfer
    notify.assert_called_once()
    assert notify.call_args.kwargs["commit"] is False
    audit.assert_called_once()
    assert audit.call_args.kwargs["commit"] is False
    _flush_before_single_commit(db)


def test_update_transfer_status_audits_before_single_commit() -> None:
    facility_id = uuid4()
    transfer_id = uuid4()
    transfer = MagicMock(id=transfer_id, source_facility_id=facility_id, destination_facility_id=uuid4(), status="REQUESTED", patient_id=uuid4())
    db = MagicMock()
    db.get.return_value = transfer

    with patch("app.referrals.service.notify_patient_event") as notify, \
         patch("app.referrals.service.record_audit") as audit:
        result = update_transfer_status(db, facility_id, transfer_id, "ACCEPTED", actor_user_id=uuid4())

    assert result is transfer
    assert transfer.status == "ACCEPTED"
    notify.assert_called_once()
    assert notify.call_args.kwargs["commit"] is False
    audit.assert_called_once()
    assert audit.call_args.kwargs["commit"] is False
    _single_commit(db)
