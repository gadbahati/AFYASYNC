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
    patient_id = uuid4()
    encounter_id = uuid4()

    claim = SimpleNamespace(
        id=claim_id,
        invoice_id=invoice_id,
        payer_id=payer_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        claim_id="CLM-20260912-TEST1234",
        status="READY",
        claim_amount=Decimal("100.00"),
        submitted_at=None,
    )
    invoice = SimpleNamespace(facility_id=facility_id)
    payer = SimpleNamespace(id=payer_id, status="ACTIVE", code="TEST-PAYER")
    encounter = SimpleNamespace(id=encounter_id, facility_id=facility_id, patient_id=patient_id, coverage_mode="SHA")
    integration = SimpleNamespace(id=integration_id, status="ACTIVE", provider="TEST-PAYER")

    db = MagicMock()
    db.scalar.side_effect = [claim, integration]
    db.get.side_effect = [invoice, payer, claim, invoice, payer, encounter]
    db.scalars.return_value = []
    queued = SimpleNamespace(transaction_id="CLM-20260912-TEST1234:attempt")

    with patch("app.claims.service.queue_transaction", return_value=queued), patch("app.claims.service.notify_patient_event"), patch("app.claims.service.record_audit"):
        result = submit_claim(db, claim_id, facility_id)

    assert result is claim
    locked_statement = db.scalar.call_args_list[0].args[0]
    assert locked_statement._for_update_arg is not None
    assert claim.status == "SUBMITTED"
    db.commit.assert_called_once()
