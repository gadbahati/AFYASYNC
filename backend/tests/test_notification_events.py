from uuid import uuid4

from app.notifications.events import EVENT_TEMPLATES, notify_patient_event


def test_notification_event_templates_are_minimal_and_supported():
    assert "LAB_RESULT_READY" in EVENT_TEMPLATES
    assert "PAYMENT_CONFIRMED" in EVENT_TEMPLATES
    assert "REFERRAL_STATUS_CHANGED" in EVENT_TEMPLATES
    for title, message in EVENT_TEMPLATES.values():
        assert title
        assert message
        assert "diagnos" not in message.lower()
        assert "result:" not in message.lower()


def test_unknown_notification_event_is_rejected():
    try:
        notify_patient_event(None, patient_id=uuid4(), event_type="UNKNOWN_EVENT")
    except ValueError as exc:
        assert str(exc) == "UNSUPPORTED_NOTIFICATION_EVENT"
    else:
        raise AssertionError("Unsupported notification event was accepted")
