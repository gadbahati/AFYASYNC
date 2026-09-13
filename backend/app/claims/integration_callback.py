from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.claims.models import Claim, ClaimResponse
from app.claims.service import ClaimsError, record_payer_response
from app.coverage.models import Payer
from app.integrations.models import Integration, IntegrationTransaction
from app.integrations.service import IntegrationError


_FINAL_STATUSES = {"REJECTED", "PARTIALLY_PAID", "PAID"}
_ALLOWED_STATUSES = {"ACCEPTED", "UNDER_REVIEW", "REJECTED", "PARTIALLY_PAID", "PAID"}


def process_claim_payer_callback(
    db: Session,
    *,
    facility_id: UUID,
    integration_id: UUID,
    claim_id: UUID,
    status: str,
    response_code: str | None,
    response_message: str | None,
    external_reference: str,
    approved_amount: Decimal | None,
) -> tuple[Claim, bool]:
    """Apply a signed payer claim response atomically and idempotently.

    Returns (claim, duplicate) where duplicate=True means the exact external
    response had already been accepted and no second business event was created.
    """
    integration = db.scalar(
        select(Integration)
        .where(Integration.id == integration_id, Integration.facility_id == facility_id)
        .with_for_update()
    )
    if integration is None:
        raise IntegrationError("INTEGRATION_NOT_FOUND")
    if integration.status != "ACTIVE":
        raise IntegrationError("INTEGRATION_NOT_ACTIVE")
    if integration.integration_type.upper() not in {"PAYER_CLAIMS", "CLAIMS"}:
        raise ClaimsError("INVALID_PAYER_INTEGRATION")

    external_reference = external_reference.strip()
    if not external_reference:
        raise ClaimsError("PAYER_EXTERNAL_REFERENCE_REQUIRED")
    if status not in _ALLOWED_STATUSES:
        raise ClaimsError("INVALID_CLAIM_RESPONSE_STATUS")

    claim = db.scalar(
        select(Claim)
        .where(Claim.id == claim_id)
        .with_for_update()
    )
    if claim is None:
        raise ClaimsError("CLAIM_NOT_FOUND")

    invoice_facility = db.scalar(
        select(Claim.id)
        .join_from(Claim, __import__("app.billing.models", fromlist=["Invoice"]).Invoice, __import__("app.billing.models", fromlist=["Invoice"]).Invoice.id == Claim.invoice_id)
        .where(Claim.id == claim.id, __import__("app.billing.models", fromlist=["Invoice"]).Invoice.facility_id == facility_id)
    )
    if invoice_facility is None:
        raise ClaimsError("FACILITY_ACCESS_DENIED")

    payer = db.get(Payer, claim.payer_id)
    if payer is None or payer.status != "ACTIVE":
        raise ClaimsError("PAYER_NOT_ACTIVE")
    if integration.provider.upper() != payer.code.upper():
        raise ClaimsError("PAYER_INTEGRATION_MISMATCH")

    transaction = db.scalar(
        select(IntegrationTransaction)
        .where(
            IntegrationTransaction.integration_id == integration_id,
            IntegrationTransaction.entity_type == "CLAIM",
            IntegrationTransaction.entity_id == claim.id,
            IntegrationTransaction.direction == "OUTBOUND",
            IntegrationTransaction.request_reference == claim.claim_id,
        )
        .order_by(IntegrationTransaction.created_at.desc())
        .with_for_update()
    )
    if transaction is None:
        raise ClaimsError("INTEGRATION_TRANSACTION_NOT_FOUND")

    existing = db.scalar(
        select(ClaimResponse)
        .where(
            ClaimResponse.claim_id == claim.id,
            ClaimResponse.external_reference == external_reference,
        )
        .limit(1)
    )
    if existing is not None:
        if existing.status == status and existing.response_code == response_code:
            return claim, True
        raise ClaimsError("DUPLICATE_PAYER_RESPONSE")

    if approved_amount is not None:
        approved_amount = Decimal(str(approved_amount)).quantize(Decimal("0.01"))
        if approved_amount > Decimal(str(claim.claim_amount)).quantize(Decimal("0.01")):
            raise ClaimsError("APPROVED_AMOUNT_EXCEEDS_CLAIM")
    if status in {"ACCEPTED", "PARTIALLY_PAID", "PAID"} and approved_amount is None:
        raise ClaimsError("APPROVED_AMOUNT_REQUIRED")
    if status == "PAID" and approved_amount == Decimal("0.00"):
        raise ClaimsError("INVALID_APPROVED_AMOUNT")

    transaction.status = "FAILED" if status == "REJECTED" else "SUCCEEDED" if status in {"ACCEPTED", "PARTIALLY_PAID", "PAID"} else "PENDING"
    transaction.external_reference = external_reference
    transaction.response_code = response_code
    transaction.response_data = {
        "status": status,
        "response_message": response_message,
        "approved_amount": str(approved_amount) if approved_amount is not None else None,
    }
    transaction.attempt_count += 1
    transaction.last_attempt_at = datetime.now(timezone.utc)

    result = record_payer_response(
        db,
        claim.id,
        facility_id,
        status,
        response_code,
        response_message,
        external_reference,
        approved_amount,
        actor_user_id=None,
        commit=False,
    )
    record_audit(
        db,
        action="PROCESS_PAYER_CALLBACK",
        resource_type="INTEGRATION_TRANSACTION",
        resource_id=str(transaction.id),
        result="SUCCESS",
        user_id=None,
        facility_id=facility_id,
        patient_id=result.patient_id,
        metadata={
            "claim_id": result.claim_id,
            "integration_id": str(integration_id),
            "external_reference": external_reference,
            "payer_status": status,
        },
        commit=False,
    )
    db.commit()
    db.refresh(result)
    return result, False
