from uuid import uuid4

import pytest

from app.notifications.events import EVENT_TEMPLATES, notify_patient_event
from app.notifications.service import NotificationError, create_notification


class DummyDB:
    def __init__(self):
        self.added = []

    def get(self, model, value):
        return None

    def add(self, value):
        self.added.append(value)

    def flush(self):
        pass


def test_notification_requires_recipient():
    with pytest.raises(NotificationError, match="NOTIFICATION_RECIPIENT_REQUIRED"):
        create_notification(DummyDB(), {"notification_type": "TEST", "title": "Title", "message": "Message"})


def test_notification_with_person_recipient_is_created_without_user_lookup():
    db = DummyDB()
    notification = create_notification(
        db,
        {
            "person_id": uuid4(),
            "notification_type": "LAB_RESULT",
            "title": "Result available",
            "message": "A laboratory result is ready for review.",
        },
        commit=False,
    )
    assert notification.notification_type == "LAB_RESULT"
    assert notification.priority == "NORMAL"
    assert db.added == [notification]


def test_claim_status_notification_is_available_and_non_clinical():
    title, message = EVENT_TEMPLATES["CLAIM_STATUS_CHANGED"]
    assert title == "Claim status updated"
    assert "claim" in message.lower()
    assert "diagnosis" not in message.lower()
    assert "result" not in message.lower()


def test_claim_event_without_portal_account_is_safe():
    db = DummyDB()
    assert notify_patient_event(
        db,
        patient_id=uuid4(),
        event_type="CLAIM_STATUS_CHANGED",
        metadata={"status": "REJECTED"},
        commit=False,
    ) is None
