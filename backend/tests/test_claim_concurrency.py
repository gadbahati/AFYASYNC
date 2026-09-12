from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.claims.service import submit_claim


def test_submit_claim_locks_claim_before_queueing() -> None:
    claim_id = uuid4()
    facility_id = uuid4()
    invoice_id = uuid4()
    payer_id = uuid4()
    integration_id = uuid4()

    claim = SimpleNamespace(
        id=claim_id,
        invoice_id=invoice_id,
        payer_id=payer_id,
        patient_id=uuid4(),
        claim_id="CLM-20260912-TEST1234",
        status="READY",
        claim_amount=Decimal("100.00"),
        submitted_at=None,
    )
    invoice = SimpleNamespace(facility_id=facility_id)
    payer = SimpleNamespace(id=payer_id, status="ACTIVE", code="TEST-PAYER")
    integration = SimpleNamespace(id=integration_id)

    db = MagicMock()
    db.scalar.side_effect = [claim, integration]
    db.get.side_effect = [invoice, payer]

    with patch("app.claims.service.queue_transaction"), patch("app.claims.service.notify_patient_event"), patch("app.claims.service.record_audit"):
        result = submit_claim(db, claim_id, facility_id)

    assert result is claim
    locked_statement = db.scalar.call_args_list[0].args[0]
    assert locked_statement._for_update_arg is not None
    assert claim.status == "SUBMITTED"
    db.commit.assert_called_once()
