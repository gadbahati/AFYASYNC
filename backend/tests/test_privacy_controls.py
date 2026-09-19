from app.security.privacy import privacy_safe_path, redact_sensitive


def test_privacy_safe_path_redacts_uuid_segments():
    assert privacy_safe_path("/api/v1/patients/550e8400-e29b-41d4-a716-446655440000") == "/api/v1/patients/:id"


def test_redact_sensitive_metadata():
    payload = {
        "provider": "SHA",
        "callback_secret": "should-not-log",
        "nested": {"access_token": "secret", "safe": "ok"},
        "long": "x" * 600,
    }
    result = redact_sensitive(payload)
    assert result["callback_secret"] == "[REDACTED]"
    assert result["nested"]["access_token"] == "[REDACTED]"
    assert len(result["long"]) <= 501
