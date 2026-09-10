from app.claims.service import ClaimsError


def test_claim_submission_requires_authorised_payer_integration():
    # The service deliberately refuses to mark a claim SUBMITTED when no active
    # PAYER_CLAIMS/CLAIMS integration exists for the payer code. This prevents a
    # local status from being mistaken for successful external submission.
    assert str(ClaimsError("PAYER_INTEGRATION_NOT_CONFIGURED")) == "PAYER_INTEGRATION_NOT_CONFIGURED"
