import hashlib
import hmac
import json
import time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.claims.service import ClaimsError, process_payer_callback
from app.integrations.service import IntegrationError, verify_callback_signature
from app.integrations.worker import MAX_INTEGRATION_ATTEMPTS, process_pending_transaction


def test_payer_callback_updates_integration_transaction_and_claim() -> None:
    facility_id = uuid4()
    integration_id = uuid4()
    claim_id = uuid4()
    integration = SimpleNamespace(id=integration_id, facility_id=facility_id, status="ACTIVE", integration_type="PAYER_CLAIMS", provider="TEST_PAYER")
    payer = SimpleNamespace(id=uuid4(), status="ACTIVE", code="TEST_PAYER")
    claim = SimpleNamespace(id=claim_id, claim_id="CLM-CALLBACK", invoice_id=uuid4(), patient_id=uuid4(), payer_id=payer.id, status="SUBMITTED")
    transaction = SimpleNamespace(id=uuid4(), integration_id=integration_id, entity_type="CLAIM", entity_id=claim_id, direction="OUTBOUND", request_reference=claim.claim_id, status="PENDING", external_reference=None, response_code=None, response_data={})
    db = MagicMock()
    db.get.side_effect = [integration, claim, payer]
    db.scalar.side_effect = [transaction, None]

    with patch("app.claims.service.record_payer_response", return_value=claim) as record_response:
        result = process_payer_callback(db, facility_id, integration_id, claim_id, "ACCEPTED", "200", "Accepted by payer", "PAYER-12345", Decimal("125.00"))

    assert result is claim
    assert transaction.status == "SUCCEEDED"
    assert transaction.external_reference == "PAYER-12345"
    assert transaction.response_code == "200"
    assert transaction.response_data["status"] == "ACCEPTED"
    record_response.assert_called_once_with(db, claim_id, facility_id, "ACCEPTED", "200", "Accepted by payer", "PAYER-12345", Decimal("125.00"), actor_user_id=None)


def test_duplicate_payer_callback_is_rejected_before_claim_mutation() -> None:
    facility_id = uuid4()
    integration_id = uuid4()
    claim_id = uuid4()
    integration = SimpleNamespace(id=integration_id, facility_id=facility_id, status="ACTIVE", integration_type="CLAIMS", provider="TEST_PAYER")
    payer = SimpleNamespace(id=uuid4(), status="ACTIVE", code="TEST_PAYER")
    claim = SimpleNamespace(id=claim_id, claim_id="CLM-DUP", invoice_id=uuid4(), patient_id=uuid4(), payer_id=payer.id, status="SUBMITTED")
    transaction = SimpleNamespace(id=uuid4(), integration_id=integration_id, entity_type="CLAIM", entity_id=claim_id, direction="OUTBOUND", request_reference=claim.claim_id, status="PENDING")
    duplicate = SimpleNamespace(id=uuid4())
    db = MagicMock()
    db.get.side_effect = [integration, claim, payer]
    db.scalar.side_effect = [transaction, duplicate]

    with pytest.raises(ClaimsError, match="DUPLICATE_PAYER_RESPONSE"):
        process_payer_callback(db, facility_id, integration_id, claim_id, "ACCEPTED", None, None, "PAYER-DUP", Decimal("50.00"))

    assert transaction.status == "PENDING"
    db.commit.assert_not_called()


def test_payer_callback_rejects_cross_facility_integration() -> None:
    facility_id = uuid4()
    integration = SimpleNamespace(id=uuid4(), facility_id=uuid4(), status="ACTIVE", integration_type="PAYER_CLAIMS", provider="TEST_PAYER")
    db = MagicMock()
    db.get.return_value = integration

    with pytest.raises(ClaimsError, match="INTEGRATION_NOT_FOUND"):
        process_payer_callback(db, facility_id, integration.id, uuid4(), "ACCEPTED", None, None, "PAYER-X", Decimal("10.00"))


def test_worker_builds_claim_payload_before_adapter_send() -> None:
    facility_id = uuid4()
    claim_id = uuid4()
    transaction = SimpleNamespace(id=uuid4(), integration_id=uuid4(), transaction_id="CLM-WORKER", entity_type="CLAIM", entity_id=claim_id, status="PENDING", attempt_count=0, response_code=None, external_reference=None, response_data={}, last_attempt_at=None)
    integration = SimpleNamespace(id=transaction.integration_id, facility_id=facility_id, status="ACTIVE")
    adapter = MagicMock()
    adapter.send.return_value = SimpleNamespace(status="RETRYING", response_code="ADAPTER_UNAVAILABLE", external_reference=None, response_data={"retryable": True})
    db = MagicMock()
    db.get.side_effect = [transaction, integration]

    payload = {"claim_id": "CLM-WORKER", "claim_amount": "75.00", "items": []}
    with patch("app.integrations.worker.build_claim_submission_payload", return_value=payload) as builder:
        result = process_pending_transaction(db, transaction.id, adapter=adapter)

    builder.assert_called_once_with(db, claim_id, facility_id)
    adapter.send.assert_called_once_with(payload, "CLM-WORKER")
    assert result.status == "RETRYING"
    assert result.attempt_count == 1
    assert result.response_code == "ADAPTER_UNAVAILABLE"


def test_callback_signature_accepts_valid_signed_payload() -> None:
    secret = "test-callback-secret"
    payload = {"status": "ACCEPTED", "external_reference": "PAYER-1", "approved_amount": "10.00"}
    timestamp = str(int(time.time()))
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()
    integration = SimpleNamespace(configuration={"callback_secret": secret})

    verify_callback_signature(integration, timestamp, f"sha256={digest}", payload)


def test_callback_signature_rejects_invalid_signature() -> None:
    integration = SimpleNamespace(configuration={"callback_secret": "test-callback-secret"})
    with pytest.raises(IntegrationError, match="INVALID_CALLBACK_SIGNATURE"):
        verify_callback_signature(integration, str(int(time.time())), "sha256=bad", {"status": "ACCEPTED"})


def test_callback_signature_rejects_expired_timestamp() -> None:
    integration = SimpleNamespace(configuration={"callback_secret": "test-callback-secret"})
    with pytest.raises(IntegrationError, match="CALLBACK_TIMESTAMP_EXPIRED"):
        verify_callback_signature(integration, str(int(time.time()) - 301), "sha256=bad", {"status": "ACCEPTED"})


def test_worker_fails_after_max_integration_attempts() -> None:
    transaction = SimpleNamespace(id=uuid4(), integration_id=uuid4(), status="RETRYING", attempt_count=MAX_INTEGRATION_ATTEMPTS, response_code=None, response_data={})
    integration = SimpleNamespace(id=transaction.integration_id, status="ACTIVE")
    db = MagicMock()
    db.get.side_effect = [transaction, integration]

    result = process_pending_transaction(db, transaction.id)

    assert result.status == "FAILED"
    assert result.response_code == "MAX_ATTEMPTS_EXCEEDED"
    assert result.response_data["max_attempts"] == MAX_INTEGRATION_ATTEMPTS
    db.commit.assert_called_once()
