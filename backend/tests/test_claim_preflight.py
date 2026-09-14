from uuid import uuid4

import pytest

from app.claims.preflight_schemas import ClaimPreflightResponse
from app.claims.preflight_service import preflight_claim
from app.claims.service import ClaimsError


def test_claim_preflight_response_defaults_are_safe():
    result = ClaimPreflightResponse(invoice_id=uuid4(), ready=False)
    assert result.ready is False
    assert result.errors == []
    assert result.warnings == []
    assert result.payer_amount == 0
    assert result.patient_amount == 0
    assert result.item_count == 0


def test_claim_preflight_response_rejects_negative_counts():
    with pytest.raises(ValueError):
        ClaimPreflightResponse(invoice_id=uuid4(), ready=False, item_count=-1)


def test_claim_preflight_response_rejects_negative_financial_totals():
    with pytest.raises(ValueError):
        ClaimPreflightResponse(invoice_id=uuid4(), ready=False, payer_amount=-0.01)
    with pytest.raises(ValueError):
        ClaimPreflightResponse(invoice_id=uuid4(), ready=False, patient_amount=-0.01)


def test_claim_preflight_hides_invoices_from_other_facilities(db_session):
    invoice_id = uuid4()
    facility_id = uuid4()
    actor_user_id = uuid4()

    with pytest.raises(ClaimsError, match="INVOICE_NOT_FOUND"):
        preflight_claim(
            db_session,
            invoice_id=invoice_id,
            facility_id=facility_id,
            actor_user_id=actor_user_id,
        )
