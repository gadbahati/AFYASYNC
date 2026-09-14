from uuid import uuid4

from app.claims.preflight_schemas import ClaimPreflightResponse


def test_claim_preflight_response_defaults_are_safe():
    result = ClaimPreflightResponse(invoice_id=uuid4(), ready=False)
    assert result.ready is False
    assert result.errors == []
    assert result.warnings == []
    assert result.payer_amount == 0
    assert result.patient_amount == 0
    assert result.item_count == 0


def test_claim_preflight_response_rejects_negative_counts():
    try:
        ClaimPreflightResponse(invoice_id=uuid4(), ready=False, item_count=-1)
    except ValueError:
        return
    raise AssertionError("negative item_count must be rejected")
