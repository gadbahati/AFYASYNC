import hashlib
import hmac
import time

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def _signed(body: bytes, timestamp: str, secret: str) -> str:
    return hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()


def test_ussd_rejects_missing_or_invalid_signature(monkeypatch):
    secret = "test-ussd-secret-with-enough-entropy"
    monkeypatch.setattr(settings, "ussd_webhook_secret", secret)
    body = b'{"session_id":"s1","phone_number":"254700000000","text":"","service_code":"*123#"}'
    with TestClient(app) as client:
        response = client.post("/api/v1/ussd/callback", content=body, headers={"X-AfyaSync-Timestamp": str(int(time.time())), "X-AfyaSync-Signature": "bad"})
    assert response.status_code == 401


def test_ussd_returns_plain_text_menu(monkeypatch):
    secret = "test-ussd-secret-with-enough-entropy"
    monkeypatch.setattr(settings, "ussd_webhook_secret", secret)
    timestamp = str(int(time.time()))
    body = b'{"session_id":"s1","phone_number":"254700000000","text":"","service_code":"*123#"}'
    with TestClient(app) as client:
        response = client.post("/api/v1/ussd/callback", content=body, headers={"X-AfyaSync-Timestamp": timestamp, "X-AfyaSync-Signature": _signed(body, timestamp, secret)})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text.startswith("CON AfyaSync")


def test_ussd_rejects_stale_timestamp(monkeypatch):
    secret = "test-ussd-secret-with-enough-entropy"
    monkeypatch.setattr(settings, "ussd_webhook_secret", secret)
    timestamp = str(int(time.time()) - 301)
    body = b'{"session_id":"s1","phone_number":"254700000000","text":"0","service_code":"*123#"}'
    with TestClient(app) as client:
        response = client.post("/api/v1/ussd/callback", content=body, headers={"X-AfyaSync-Timestamp": timestamp, "X-AfyaSync-Signature": _signed(body, timestamp, secret)})
    assert response.status_code == 401
