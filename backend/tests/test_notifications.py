from uuid import uuid4

import pytest

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
