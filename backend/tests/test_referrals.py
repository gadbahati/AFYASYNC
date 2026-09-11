from types import SimpleNamespace
from uuid import uuid4

from app.referrals.service import (
    REFERRAL_TRANSITIONS,
    TRANSFER_TRANSITIONS,
    create_referral,
    create_transfer,
    update_referral_status,
    update_transfer_status,
)


class DummyDB:
    def __init__(self, values):
        self.values = values
        self.added = []

    def get(self, model, value):
        return self.values.get(model)

    def add(self, value):
        self.added.append(value)

    def commit(self):
        pass

    def refresh(self, value):
        if getattr(value, "id", None) is None:
            value.id = uuid4()


class DummyNotificationRecorder:
    def __init__(self):
        self.calls = []

    def __call__(self, db, **kwargs):
        self.calls.append(kwargs)
        return None


def test_referral_lifecycle_transitions_are_one_way():
    assert REFERRAL_TRANSITIONS["CREATED"] == {"SENT", "CANCELLED"}
    assert REFERRAL_TRANSITIONS["SENT"] == {"ACCEPTED", "DECLINED", "CANCELLED"}
    assert REFERRAL_TRANSITIONS["ACCEPTED"] == {"IN_PROGRESS", "CANCELLED"}
    assert REFERRAL_TRANSITIONS["IN_PROGRESS"] == {"COMPLETED", "CANCELLED"}
    assert REFERRAL_TRANSITIONS["COMPLETED"] == set()


def test_transfer_lifecycle_requires_ordered_states():
    assert TRANSFER_TRANSITIONS["REQUESTED"] == {"ACCEPTED", "CANCELLED"}
    assert TRANSFER_TRANSITIONS["ACCEPTED"] == {"IN_TRANSIT", "CANCELLED"}
    assert TRANSFER_TRANSITIONS["IN_TRANSIT"] == {"ARRIVED", "CANCELLED"}
    assert TRANSFER_TRANSITIONS["ARRIVED"] == set()


def test_create_referral_notifies_patient_with_minimal_metadata(monkeypatch):
    import app.referrals.service as service

    recorder = DummyNotificationRecorder()
    monkeypatch.setattr(service, "notify_patient_event", recorder)

    facility_id = uuid4()
    destination_id = uuid4()
    patient_id = uuid4()
    encounter = SimpleNamespace(id=uuid4(), patient_id=patient_id, facility_id=facility_id, status="OPEN")
    staff = SimpleNamespace(facility_id=facility_id, status="ACTIVE")
    destination = SimpleNamespace(id=destination_id, status="ACTIVE")
    db = DummyDB({service.Encounter: encounter, service.Staff: staff, service.Facility: destination})

    referral = create_referral(
        db,
        facility_id,
        uuid4(),
        {"encounter_id": encounter.id, "destination_facility_id": destination_id, "reason": "Specialist review"},
    )

    assert referral.status == "CREATED"
    assert recorder.calls == [
        {
            "patient_id": patient_id,
            "event_type": "REFERRAL_CREATED",
            "facility_id": facility_id,
            "metadata": {"status": "CREATED"},
            "actor_user_id": None,
            "commit": False,
        }
    ]


def test_update_referral_status_notifies_patient_with_status_only(monkeypatch):
    import app.referrals.service as service

    recorder = DummyNotificationRecorder()
    monkeypatch.setattr(service, "notify_patient_event", recorder)

    facility_id = uuid4()
    referral = SimpleNamespace(
        id=uuid4(),
        patient_id=uuid4(),
        source_facility_id=facility_id,
        destination_facility_id=uuid4(),
        status="CREATED",
    )
    db = DummyDB({service.Referral: referral})

    update_referral_status(db, facility_id, referral.id, "SENT")

    assert recorder.calls == [
        {
            "patient_id": referral.patient_id,
            "event_type": "REFERRAL_STATUS_CHANGED",
            "facility_id": facility_id,
            "metadata": {"status": "SENT"},
            "actor_user_id": None,
            "commit": False,
        }
    ]


def test_create_transfer_notifies_patient_with_minimal_metadata(monkeypatch):
    import app.referrals.service as service

    recorder = DummyNotificationRecorder()
    monkeypatch.setattr(service, "notify_patient_event", recorder)

    facility_id = uuid4()
    destination_id = uuid4()
    patient_id = uuid4()
    encounter = SimpleNamespace(id=uuid4(), patient_id=patient_id, facility_id=facility_id, status="OPEN")
    staff = SimpleNamespace(facility_id=facility_id, status="ACTIVE")
    destination = SimpleNamespace(id=destination_id, status="ACTIVE")
    db = DummyDB({service.Encounter: encounter, service.Staff: staff, service.Facility: destination})

    transfer = create_transfer(
        db,
        facility_id,
        uuid4(),
        {"encounter_id": encounter.id, "destination_facility_id": destination_id, "reason": "Higher level care"},
    )

    assert transfer.status == "REQUESTED"
    assert recorder.calls == [
        {
            "patient_id": patient_id,
            "event_type": "TRANSFER_REQUESTED",
            "facility_id": facility_id,
            "metadata": {"status": "REQUESTED"},
            "actor_user_id": None,
            "commit": False,
        }
    ]


def test_update_transfer_status_notifies_patient_with_status_only(monkeypatch):
    import app.referrals.service as service

    recorder = DummyNotificationRecorder()
    monkeypatch.setattr(service, "notify_patient_event", recorder)

    facility_id = uuid4()
    transfer = SimpleNamespace(
        id=uuid4(),
        patient_id=uuid4(),
        source_facility_id=facility_id,
        destination_facility_id=uuid4(),
        status="REQUESTED",
    )
    db = DummyDB({service.Transfer: transfer})

    update_transfer_status(db, facility_id, transfer.id, "ACCEPTED")

    assert recorder.calls == [
        {
            "patient_id": transfer.patient_id,
            "event_type": "TRANSFER_STATUS_CHANGED",
            "facility_id": facility_id,
            "metadata": {"status": "ACCEPTED"},
            "actor_user_id": None,
            "commit": False,
        }
    ]
