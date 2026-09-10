from uuid import uuid4


def test_lab_notification_event_is_supported():
    from app.notifications.events import EVENT_TEMPLATES

    assert "LAB_RESULT_READY" in EVENT_TEMPLATES


def test_lab_notification_template_does_not_expose_result_text():
    from app.notifications.events import EVENT_TEMPLATES

    message = EVENT_TEMPLATES["LAB_RESULT_READY"][1]
    assert "result:" not in message.lower()
    assert "diagnos" not in message.lower()
