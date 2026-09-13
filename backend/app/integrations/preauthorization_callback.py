from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.integrations.models import Integration, IntegrationTransaction
from app.integrations.service import IntegrationError
from app.preauthorizations.models import PreAuthorization


class PreAuthorizationCallbackError(ValueError):
    pass


_ALLOWED = {"AUTHORIZED", "REJECTED", "AUTHORIZED_PENDING_VISIT", "PENDING"}


def process_preauthorization_callback(
    db: Session,
    *,
    integration_id: UUID,
    authorization_id: UUID,
    status: str,
    response_code: str | None,
    response_message: str | None,
    external_reference: str,
    approved_amount: Decimal | None,
) -> PreAuthorization:
    integration = db.get(Integration, integration_id)
    if integration is None:
        raise IntegrationError("INTEGRATION_NOT_FOUND")
    authorization = db.get(PreAuthorization, authorization_id)
    if authorization is None:
        raise PreAuthorizationCallbackError("PREAUTH_NOT_FOUND")
    if authorization.facility_id != integration.facility_id:
        raise PreAuthorizationCallbackError("FACILITY_ACCESS_DENIED")
    if status not in _ALLOWED:
        raise PreAuthorizationCallbackError("INVALID_PREAUTH_CALLBACK_STATUS")
    if not external_reference.strip():
        raise PreAuthorizationCallbackError("PREAUTH_EXTERNAL_REFERENCE_REQUIRED")
    if approved_amount is not None and approved_amount > Decimal(str(authorization.requested_amount)):
        raise PreAuthorizationCallbackError("APPROVED_AMOUNT_EXCEEDS_REQUEST")
    if status == "REJECTED" and approved_amount not in (None, Decimal("0")):
        raise PreAuthorizationCallbackError("REJECTED_AMOUNT_MUST_BE_ZERO")

    transaction = db.scalar(
        select(IntegrationTransaction).where(
            IntegrationTransaction.integration_id == integration_id,
            IntegrationTransaction.entity_type == "PREAUTHORIZATION",
            IntegrationTransaction.entity_id == authorization_id,
            IntegrationTransaction.direction == "OUTBOUND",
        )
    )
    if transaction is None:
        raise PreAuthorizationCallbackError("PREAUTH_TRANSACTION_NOT_FOUND")

    if authorization.status in {"AUTHORIZED", "REJECTED", "AUTHORIZED_PENDING_VISIT"}:
        if transaction.external_reference == external_reference and transaction.response_code == response_code:
            return authorization
        raise PreAuthorizationCallbackError("DUPLICATE_PREAUTH_RESPONSE")

    transaction.status = "SUCCEEDED" if status in {"AUTHORIZED", "AUTHORIZED_PENDING_VISIT"} else "FAILED"
    transaction.external_reference = external_reference
    transaction.response_code = response_code
    transaction.response_data = {"status": status, "message": response_message, "approved_amount": str(approved_amount) if approved_amount is not None else None}
    authorization.status = status
    authorization.approved_amount = approved_amount or Decimal("0")
    authorization.external_reference = external_reference

    db.flush()
    record_audit(
        db,
        action="PREAUTHORIZATION_PAYER_CALLBACK",
        resource_type="PREAUTHORIZATION",
        resource_id=str(authorization.id),
        result=status,
        user_id=None,
        facility_id=authorization.facility_id,
        patient_id=authorization.patient_id,
        metadata={"integration_id": str(integration_id), "transaction_id": transaction.transaction_id, "response_code": response_code, "external_reference": external_reference},
        commit=False,
    )
    db.commit()
    db.refresh(authorization)
    return authorization
