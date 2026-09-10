from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4
import json

import pytest

from app.billing.service import BillingError, create_charge, process_payment_callback, record_payment
from app.claims.service import ClaimsError, record_payer_response, submit_claim
from app.integrations.adapters import AdapterResult, HttpJsonAdapter, UnconfiguredAdapter, build_adapter
from app.integrations.worker import _build_payment_submission_payload


def test_charge_cannot_cross_facility_boundary() -> None:
    facility_a = uuid4()
    facility_b = uuid4()
    encounter = SimpleNamespace(id=uuid4(), facility_id=facility_b, patient_id=uuid4())
    db = MagicMock()
    db.get.return_value = encounter

    with pytest.raises(BillingError, match="FACILITY_ACCESS_DENIED"):
        create_charge(db, facility_a, {"encounter_id": encounter.id, "service_id": uuid4(), "quantity": 1, "source_type": "CONSULTATION"})
    db.commit.assert_not_called()


def test_payment_idempotency_rejects_reuse_for_different_amount() -> None:
    facility_id = uuid4()
    invoice = SimpleNamespace(id=uuid4(), facility_id=facility_id, patient_id=uuid4(), patient_amount=Decimal("100.00"), status="OPEN")
    existing = SimpleNamespace(invoice_id=invoice.id, amount=Decimal("25.00"))
    db = MagicMock()
    db.get.return_value = invoice
    db.scalar.return_value = existing
    with pytest.raises(BillingError, match="IDEMPOTENCY_KEY_REUSED"):
        record_payment(db, facility_id, {"invoice_id": invoice.id, "amount": "30.00", "payment_method": "MOBILE_MONEY", "idempotency_key": "same-request"})
    db.commit.assert_not_called()


def test_successful_payment_records_audit() -> None:
    facility_id = uuid4()
    invoice = SimpleNamespace(id=uuid4(), facility_id=facility_id, patient_id=uuid4(), patient_amount=Decimal("100.00"), status="OPEN")
    db = MagicMock()
    db.get.return_value = invoice
    db.scalar.return_value = None
    db.scalars.return_value = []
    with patch("app.billing.service.record_audit") as audit:
        payment = record_payment(db, facility_id, {"invoice_id": invoice.id, "amount": "40.00", "payment_method": "CASH", "idempotency_key": "audit-test"}, actor_user_id=uuid4())
    assert payment.amount == Decimal("40.00")
    assert invoice.status == "PARTIALLY_PAID"
    audit.assert_called_once()
    assert audit.call_args.kwargs["action"] == "RECORD_PAYMENT"
    assert audit.call_args.kwargs["result"] == "SUCCESS"


def test_claim_submission_never_marks_invoice_paid() -> None:
    facility_id = uuid4()
    payer_id = uuid4()
    invoice = SimpleNamespace(id=uuid4(), facility_id=facility_id, status="CLAIM_PENDING")
    payer = SimpleNamespace(id=payer_id, status="ACTIVE", code="TEST_PAYER")
    claim = SimpleNamespace(id=uuid4(), claim_id="CLM-TEST", invoice_id=invoice.id, patient_id=uuid4(), payer_id=payer_id, status="READY", submitted_at=None)
    integration = SimpleNamespace(id=uuid4(), status="ACTIVE")
    db = MagicMock()
    db.get.side_effect = [claim, invoice, payer]
    db.scalar.return_value = integration
    with patch("app.claims.service.queue_transaction") as queue_transaction, patch("app.claims.service.record_audit"):
        result = submit_claim(db, claim.id, facility_id, actor_user_id=uuid4())
    assert result.status == "SUBMITTED"
    assert result.submitted_at is not None
    assert invoice.status == "CLAIM_PENDING"
    queue_transaction.assert_called_once_with(db, facility_id, integration.id, claim.claim_id, "CLAIM", claim.id, "OUTBOUND", claim.claim_id)
    assert db.add.call_count == 1


def test_claim_submission_requires_authorised_payer_integration() -> None:
    facility_id = uuid4()
    payer_id = uuid4()
    invoice = SimpleNamespace(id=uuid4(), facility_id=facility_id)
    payer = SimpleNamespace(id=payer_id, status="ACTIVE", code="NO_INTEGRATION")
    claim = SimpleNamespace(id=uuid4(), claim_id="CLM-NO-INTEGRATION", invoice_id=invoice.id, patient_id=uuid4(), payer_id=payer_id, status="READY", submitted_at=None)
    db = MagicMock()
    db.get.side_effect = [claim, invoice, payer]
    db.scalar.return_value = None
    with pytest.raises(ClaimsError, match="PAYER_INTEGRATION_NOT_CONFIGURED"):
        submit_claim(db, claim.id, facility_id)
    assert claim.status == "READY"
    db.commit.assert_not_called()


def test_claim_response_is_facility_scoped() -> None:
    facility_a = uuid4()
    facility_b = uuid4()
    claim = SimpleNamespace(id=uuid4(), invoice_id=uuid4(), patient_id=uuid4())
    invoice = SimpleNamespace(facility_id=facility_b)
    db = MagicMock()
    db.get.side_effect = [claim, invoice]
    with pytest.raises(ClaimsError, match="FACILITY_ACCESS_DENIED"):
        record_payer_response(db, claim.id, facility_a, "ACCEPTED", None, None, None, None)
    db.commit.assert_not_called()


def test_unconfigured_adapter_never_reports_success() -> None:
    result = UnconfiguredAdapter().send({"claim_id": "CLM-1"}, "CLM-1")
    assert result.status == "RETRYING"
    assert result.response_code == "ADAPTER_NOT_CONFIGURED"


def test_build_adapter_requires_https() -> None:
    with pytest.raises(ValueError, match="HTTPS_ENDPOINT_REQUIRED"):
        build_adapter({"adapter_type": "http_json", "endpoint": "http://payer.example.test/claims"})


def test_http_adapter_requires_environment_credential_when_configured() -> None:
    adapter = HttpJsonAdapter(endpoint="https://payer.example.test/claims", credential_env="AFYASYNC_TEST_TOKEN")
    with patch.dict("os.environ", {}, clear=True):
        result = adapter.send({"claim_id": "CLM-1"}, "CLM-1")
    assert result.status == "RETRYING"
    assert result.response_code == "ADAPTER_CREDENTIAL_NOT_CONFIGURED"


def test_http_adapter_sends_json_and_idempotency_key() -> None:
    class FakeResponse:
        status = 202
        def read(self):
            return json.dumps({"external_reference": "EXT-1", "accepted": True}).encode()
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
    with patch.dict("os.environ", {"AFYASYNC_TEST_TOKEN": "secret"}, clear=True), patch("app.integrations.adapters.urlopen", return_value=FakeResponse()) as urlopen_mock:
        result = HttpJsonAdapter(endpoint="https://payer.example.test/claims", credential_env="AFYASYNC_TEST_TOKEN").send({"claim_id": "CLM-1"}, "CLM-1")
    request = urlopen_mock.call_args.args[0]
    assert request.full_url == "https://payer.example.test/claims"
    assert request.get_header("Idempotency-key") == "CLM-1"
    assert request.get_header("Authorization") == "Bearer secret"
    assert json.loads(request.data.decode()) == {"claim_id": "CLM-1"}
    assert result == AdapterResult(status="SUCCEEDED", response_code="202", external_reference="EXT-1", response_data={"external_reference": "EXT-1", "accepted": True})


def test_provider_payment_starts_created_and_queues_transaction() -> None:
    facility_id = uuid4()
    invoice = SimpleNamespace(id=uuid4(), facility_id=facility_id, patient_id=uuid4(), patient_amount=Decimal("100.00"), status="OPEN")
    integration = SimpleNamespace(id=uuid4(), status="ACTIVE", provider="TEST_PAY")
    db = MagicMock()
    db.get.return_value = invoice
    db.scalar.side_effect = [None, integration]
    db.scalars.return_value = []
    payment = record_payment(db, facility_id, {"invoice_id": invoice.id, "amount": "40.00", "payment_method": "MOBILE_MONEY", "provider": "TEST_PAY", "idempotency_key": "provider-1"})
    assert payment.status == "CREATED"
    assert invoice.status == "OPEN"
    added = [call.args[0] for call in db.add.call_args_list]
    assert any(getattr(item, "entity_type", None) == "PAYMENT" for item in added)


def test_provider_payment_requires_active_integration() -> None:
    facility_id = uuid4()
    invoice = SimpleNamespace(id=uuid4(), facility_id=facility_id, patient_id=uuid4(), patient_amount=Decimal("100.00"), status="OPEN")
    db = MagicMock()
    db.get.return_value = invoice
    db.scalar.side_effect = [None, None]
    db.scalars.return_value = []
    with pytest.raises(BillingError, match="PAYMENT_INTEGRATION_NOT_CONFIGURED"):
        record_payment(db, facility_id, {"invoice_id": invoice.id, "amount": "40.00", "payment_method": "CARD", "provider": "MISSING_PROVIDER"})


def test_payment_callback_confirms_and_updates_invoice() -> None:
    facility_id = uuid4()
    integration_id = uuid4()
    payment_id = uuid4()
    invoice_id = uuid4()
    integration = SimpleNamespace(id=integration_id, facility_id=facility_id, status="ACTIVE", integration_type="PAYMENTS", provider="TEST_PAY")
    payment = SimpleNamespace(id=payment_id, facility_id=facility_id, patient_id=uuid4(), provider="TEST_PAY", status="CREATED", external_reference=None, amount=Decimal("40.00"), invoice_id=invoice_id, transaction_id="AFY-TXN-callback")
    invoice = SimpleNamespace(id=invoice_id, facility_id=facility_id, patient_amount=Decimal("100.00"), status="OPEN")
    transaction = SimpleNamespace(status="PENDING", response_code=None, response_data={}, external_reference=None)
    db = MagicMock()
    db.get.side_effect = [integration, payment, invoice]
    db.scalar.side_effect = [transaction, None]
    db.scalars.return_value = []
    result = process_payment_callback(db, facility_id, integration_id, payment_id, "CONFIRMED", "EXT-123", "00", "Paid")
    assert result.status == "CONFIRMED"
    assert result.external_reference == "EXT-123"
    assert invoice.status == "PARTIALLY_PAID"
    assert transaction.status == "SUCCEEDED"
    assert transaction.external_reference == "EXT-123"


def test_payment_callback_rejects_cross_facility_payment() -> None:
    facility_a = uuid4()
    facility_b = uuid4()
    integration = SimpleNamespace(id=uuid4(), facility_id=facility_a, status="ACTIVE", integration_type="PAYMENTS", provider="TEST_PAY")
    payment = SimpleNamespace(id=uuid4(), facility_id=facility_b, provider="TEST_PAY")
    db = MagicMock()
    db.get.side_effect = [integration, payment]
    with pytest.raises(BillingError, match="FACILITY_ACCESS_DENIED"):
        process_payment_callback(db, facility_a, integration.id, payment.id, "CONFIRMED", "EXT-123")


def test_payment_submission_payload_is_facility_scoped() -> None:
    facility_id = uuid4()
    payment = SimpleNamespace(id=uuid4(), facility_id=facility_id, invoice_id=uuid4(), patient_id=uuid4(), amount=Decimal("25.00"), transaction_id="AFY-TXN-1", payment_method="CARD", provider="TEST_PAY", external_reference=None)
    invoice = SimpleNamespace(id=payment.invoice_id, facility_id=facility_id, invoice_id="INV-TEST")
    db = MagicMock()
    db.get.side_effect = [payment, invoice]
    payload = _build_payment_submission_payload(db, payment.id, facility_id)
    assert payload["transaction_id"] == payment.transaction_id
    assert payload["invoice_number"] == invoice.invoice_id
    assert payload["amount"] == "25.00"
