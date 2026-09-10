from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.billing.service import BillingError, create_charge, record_payment
from app.claims.service import ClaimsError, record_payer_response, submit_claim


def test_charge_cannot_cross_facility_boundary() -> None:
    facility_a = uuid4()
    facility_b = uuid4()
    encounter = SimpleNamespace(id=uuid4(), facility_id=facility_b, patient_id=uuid4())
    db = MagicMock()
    db.get.return_value = encounter

    with pytest.raises(BillingError, match="FACILITY_ACCESS_DENIED"):
        create_charge(
            db,
            facility_a,
            {"encounter_id": encounter.id, "service_id": uuid4(), "quantity": 1, "source_type": "CONSULTATION"},
        )

    db.commit.assert_not_called()


def test_payment_idempotency_rejects_reuse_for_different_amount() -> None:
    facility_id = uuid4()
    invoice = SimpleNamespace(
        id=uuid4(),
        facility_id=facility_id,
        patient_id=uuid4(),
        patient_amount=Decimal("100.00"),
        status="OPEN",
    )
    existing = SimpleNamespace(invoice_id=invoice.id, amount=Decimal("25.00"))
    db = MagicMock()
    db.get.return_value = invoice
    db.scalar.return_value = existing

    with pytest.raises(BillingError, match="IDEMPOTENCY_KEY_REUSED"):
        record_payment(
            db,
            facility_id,
            {
                "invoice_id": invoice.id,
                "amount": "30.00",
                "payment_method": "MOBILE_MONEY",
                "idempotency_key": "same-request",
            },
        )

    db.commit.assert_not_called()


def test_successful_payment_records_audit() -> None:
    facility_id = uuid4()
    invoice = SimpleNamespace(
        id=uuid4(),
        facility_id=facility_id,
        patient_id=uuid4(),
        patient_amount=Decimal("100.00"),
        status="OPEN",
    )
    db = MagicMock()
    db.get.return_value = invoice
    db.scalar.return_value = None
    db.scalars.return_value = []

    with patch("app.billing.service.record_audit") as audit:
        payment = record_payment(
            db,
            facility_id,
            {
                "invoice_id": invoice.id,
                "amount": "40.00",
                "payment_method": "CASH",
                "idempotency_key": "audit-test",
            },
            actor_user_id=uuid4(),
        )

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
    claim = SimpleNamespace(
        id=uuid4(),
        claim_id="CLM-TEST",
        invoice_id=invoice.id,
        patient_id=uuid4(),
        payer_id=payer_id,
        status="READY",
        submitted_at=None,
    )
    integration = SimpleNamespace(id=uuid4(), status="ACTIVE")
    db = MagicMock()
    db.get.side_effect = [claim, invoice, payer]
    db.scalar.return_value = integration

    with patch("app.claims.service.record_audit"):
        result = submit_claim(db, claim.id, facility_id, actor_user_id=uuid4())

    assert result.status == "SUBMITTED"
    assert result.submitted_at is not None
    assert invoice.status == "CLAIM_PENDING"
    db.add.assert_called_once()


def test_claim_submission_requires_authorised_payer_integration() -> None:
    facility_id = uuid4()
    payer_id = uuid4()
    invoice = SimpleNamespace(id=uuid4(), facility_id=facility_id)
    payer = SimpleNamespace(id=payer_id, status="ACTIVE", code="NO_INTEGRATION")
    claim = SimpleNamespace(
        id=uuid4(),
        claim_id="CLM-NO-INTEGRATION",
        invoice_id=invoice.id,
        patient_id=uuid4(),
        payer_id=payer_id,
        status="READY",
        submitted_at=None,
    )
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
        record_payer_response(
            db,
            claim.id,
            facility_a,
            "ACCEPTED",
            None,
            None,
            None,
            None,
        )

    db.commit.assert_not_called()
