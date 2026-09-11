from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.notifications.service import NotificationError, list_notifications, mark_notification_read


def _notification(user_id, read_at=None):
    return SimpleNamespace(id=uuid4(), user_id=user_id, read_at=read_at)


def test_mark_notification_read_rejects_notification_owned_by_another_user() -> None:
    owner_id = uuid4()
    requester_id = uuid4()
    notification = _notification(owner_id)
    db = MagicMock()
    db.get.return_value = notification

    with pytest.raises(NotificationError, match="NOTIFICATION_NOT_FOUND"):
        mark_notification_read(db, requester_id, notification.id)

    assert notification.read_at is None
    db.commit.assert_not_called()


def test_mark_notification_read_marks_own_unread_notification() -> None:
    user_id = uuid4()
    notification = _notification(user_id)
    db = MagicMock()
    db.get.return_value = notification

    result = mark_notification_read(db, user_id, notification.id)

    assert result is notification
    assert notification.read_at is not None
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(notification)


def test_mark_notification_read_is_idempotent_for_already_read_notification() -> None:
    user_id = uuid4()
    notification = _notification(user_id, read_at="already-read-sentinel")
    db = MagicMock()
    db.get.return_value = notification

    result = mark_notification_read(db, user_id, notification.id)

    assert result is notification
    assert notification.read_at == "already-read-sentinel"
    db.commit.assert_not_called()


def test_mark_notification_read_rejects_missing_notification() -> None:
    db = MagicMock()
    db.get.return_value = None

    with pytest.raises(NotificationError, match="NOTIFICATION_NOT_FOUND"):
        mark_notification_read(db, uuid4(), uuid4())

    db.commit.assert_not_called()


def test_list_notifications_query_is_scoped_to_the_requesting_user() -> None:
    user_id = uuid4()
    other_user_id = uuid4()
    db = MagicMock()
    db.scalars.return_value = []
    db.scalar.return_value = 0

    list_notifications(db, user_id)

    scalars_stmt = db.scalars.call_args[0][0]
    compiled = str(scalars_stmt.compile(compile_kwargs={"literal_binds": True}))
    assert user_id.hex in compiled
    assert other_user_id.hex not in compiled

    count_stmt = db.scalar.call_args[0][0]
    compiled_count = str(count_stmt.compile(compile_kwargs={"literal_binds": True}))
    assert user_id.hex in compiled_count
