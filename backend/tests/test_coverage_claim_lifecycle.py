from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.claims.service import ClaimsError, record_payer_response, reconcile_claim
from app.coverage.service import calculate_charge_responsibility


def test_fixed_copay_is_minimum_patient_responsibility() -> None:
    db = MagicMock()
    rule = SimpleNamespace(
        id=uuid4(), payer_plan_id=None, service_code="CONSULT", service_type="CONSULTATION",
        payer_percent=Decimal("100"), fixed_patient_copay=Decimal("50"), max_covered_amount=None,
        status="ACTIVE", effective_from=None, effective_to=None, created_at=None,
    )
    coverage = SimpleNamespace(payer_id=uuid4(), payer_plan_id=None)
    db.scalars.return_value.all.return_value = [rule]

    payer, patient, _ = calculate_charge_responsibility(db, coverage, amount=Decimal("200"), service_code="CONSULT", service_type="CONSULTATION")
    assert payer == Decimal("150.00")
    assert patient == Decimal("50.00")


def test_paid_response_requires_approved_amount() -> None:
    claim = SimpleNamespace(id=uuid4(), invoice_id=uuid4(), status="ACCEPTED", claim_amount=Decimal("100"), approved_amount=Decimal("0"), patient_id=uuid4())
    invoice = SimpleNamespace(facility_id=uuid4())
    db = MagicMock()
    db.scalar.return_value = claim
    db.get.return_value = invoice

    with pytest.raises(ClaimsError, match="APPROVED_AMOUNT_REQUIRED"):
        record_payer_response(db, claim.id, invoice.facility_id, "PAID", None, None, None, None)


def test_reconciliation_cannot_overpay() -> None:
    claim = SimpleNamespace(id=uuid4(), invoice_id=uuid4(), status="ACCEPTED", claim_amount=Decimal("100"), approved_amount=Decimal("80"), paid_amount=Decimal("0"), patient_id=uuid4())
    invoice = SimpleNamespace(facility_id=uuid4())
    db = MagicMock()
    db.get.side_effect = [claim, invoice]
    db.scalar.return_value = None

    with pytest.raises(ClaimsError, match="RECEIVED_AMOUNT_EXCEEDS_EXPECTED"):
        reconcile_claim(db, claim.id, invoice.facility_id, uuid4(), Decimal("81"))

    db.commit.assert_not_called()
