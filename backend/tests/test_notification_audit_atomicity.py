from unittest.mock import patch
from uuid import uuid4

from app.notifications.service import create_notification


class AuditDB:
    def __init__(self):
        self.events = []

    def add(self, value):
        self.events.append(("add", value))

    def flush(self):
        self.events.append(("flush", None))

    def commit(self):
        self.events.append(("commit", None))

    def refresh(self, value):
        self.events.append(("refresh", value))


def test_notification_audit_is_written_before_commit() -> None:
    db = AuditDB()
    actor_id = uuid4()

    with patch("app.notifications.service.record_audit") as audit:
        notification = create_notification(
            db,
            {
                "person_id": uuid4(),
                "facility_id": uuid4(),
                "notification_type": "TEST",
                "title": "Title",
                "message": "Message",
            },
            actor_user_id=actor_id,
        )

    audit.assert_called_once()
    assert audit.call_args.kwargs["commit"] is False
    assert [event[0] for event in db.events] == ["add", "flush", "commit", "refresh"]
    assert notification in [event[1] for event in db.events if event[0] == "refresh"]


def test_notification_audit_respects_outer_transaction_when_commit_false() -> None:
    db = AuditDB()

    with patch("app.notifications.service.record_audit") as audit:
        create_notification(
            db,
            {
                "person_id": uuid4(),
                "notification_type": "TEST",
                "title": "Title",
                "message": "Message",
            },
            actor_user_id=uuid4(),
            commit=False,
        )

    audit.assert_called_once()
    assert audit.call_args.kwargs["commit"] is False
    assert [event[0] for event in db.events] == ["add", "flush"]
