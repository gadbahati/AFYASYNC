from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.coverage.models import Payer
from app.integrations.models import Integration, IntegrationTransaction
from app.integrations.service import IntegrationError
from app.preauthorizations.models import PreAuthorization


class PreAuthorizationCallbackError(ValueError):
    pass


_FINAL_STATUSES = {"AUTHORIZED", "REJECTED", "AUTHORIZED_PENDING_VISIT"}
_ALLOWED = _FINAL_STATUSES | {"PENDING"}


def process_preauthorization_callback(db: Session, *, integration_id: UUID, authorization_id: UUID, status: str, response_code: str | None, response_message: str | None, external_reference: str, approved_amount: Decimal | None) -> PreAuthorization:
    integration = db.get(Integration, integration_id)
    if integration is None:
        raise IntegrationError("INTEGRATION_NOT_FOUND")
    if integration.status != "ACTIVE":
        raise IntegrationError("INTEGRATION_NOT_ACTIVE")
    if integration.integration_type.upper() not in {"PAYER", "SHA", "HEALTH_PAYER"}:
        raise PreAuthorizationCallbackError("INVALID_PAYER_INTEGRATION")

    authorization = db.scalar(select(PreAuthorization).where(PreAuthorization.id == authorization_id).with_for_update())
    if authorization is None:
        raise PreAuthorizationCallbackError("PREAUTH_NOT_FOUND")
    if authorization.facility_id != integration.facility_id:
        raise PreAuthorizationCallbackError("FACILITY_ACCESS_DENIED")

    payer = db.get(Payer, authorization.payer_id)
    if payer is None or payer.status != "ACTIVE":
        raise PreAuthorizationCallbackError("PAYER_NOT_ACTIVE")
    if integration.provider.strip().upper() != payer.code.strip().upper():
        raise PreAuthorizationCallbackError("PAYER_INTEGRATION_MISMATCH")

    status = status.strip().upper()
    if status not in _ALLOWED:
        raise PreAuthorizationCallbackError("INVALID_PREAUTH_CALLBACK_STATUS")
    external_reference = external_reference.strip()
    if not external_reference:
        raise PreAuthorizationCallbackError("PREAUTH_EXTERNAL_REFERENCE_REQUIRED")

    requested_amount = Decimal(str(authorization.requested_amount)).quantize(Decimal("0.01"))
    if approved_amount is not None:
        approved_amount = Decimal(str(approved_amount)).quantize(Decimal("0.01"))
        if approved_amount > requested_amount:
            raise PreAuthorizationCallbackError("APPROVED_AMOUNT_EXCEEDS_REQUEST")
    if status in {"AUTHORIZED", "AUTHORIZED_PENDING_VISIT"} and approved_amount is None:
        raise PreAuthorizationCallbackError("APPROVED_AMOUNT_REQUIRED")
    if status == "REJECTED" and approved_amount not in (None, Decimal("0.00")):
        raise PreAuthorizationCallbackError("REJECTED_AMOUNT_MUST_BE_ZERO")
    if status in {"AUTHORIZED", "AUTHORIZED_PENDING_VISIT"} and approved_amount == Decimal("0.00"):
        raise PreAuthorizationCallbackError("INVALID_APPROVED_AMOUNT")

    transaction = db.scalar(
        select(IntegrationTransaction)
        .where(
            IntegrationTransaction.integration_id == integration_id,
            IntegrationTransaction.entity_type == "PREAUTHORIZATION",
            IntegrationTransaction.entity_id == authorization_id,
            IntegrationTransaction.direction == "OUTBOUND",
            IntegrationTransaction.request_reference == authorization.authorization_number,
        )
        .order_by(IntegrationTransaction.created_at.desc())
        .with_for_update()
    )
    if transaction is None:
        raise PreAuthorizationCallbackError("PREAUTH_TRANSACTION_NOT_FOUND")

    if authorization.status in _FINAL_STATUSES:
        if transaction.external_reference == external_reference and transaction.response_code == response_code and transaction.response_data.get("status") == status:
            return authorization
        raise PreAuthorizationCallbackError("DUPLICATE_PREAUTH_RESPONSE")

    if transaction.status == "SUCCEEDED" and transaction.external_reference:
        if transaction.external_reference == external_reference and transaction.response_data.get("status") == status:
            return authorization
        raise PreAuthorizationCallbackError("DUPLICATE_PREAUTH_RESPONSE")

    transaction.status = "SUCCEEDED"
    transaction.external_reference = external_reference
    transaction.response_code = response_code
    transaction.response_data = {"status": status, "message": response_message, "approved_amount": str(approved_amount) if approved_amount is not None else None}
    transaction.last_attempt_at = datetime.now(timezone.utc)
    transaction.attempt_count += 1

    authorization.status = status
    authorization.approved_amount = approved_amount if approved_amount is not None else Decimal("0.00")
    authorization.external_reference = external_reference
    if status in _FINAL_STATUSES:
        authorization.decided_at = datetime.now(timezone.utc)

    db.flush()
    record_audit(db, action="PREAUTHORIZATION_PAYER_CALLBACK", resource_type="PREAUTHORIZATION", resource_id=str(authorization.id), result=status, user_id=None, facility_id=authorization.facility_id, patient_id=authorization.patient_id, metadata={"integration_id": str(integration_id), "transaction_id": transaction.transaction_id, "response_code": response_code, "external_reference": external_reference, "approved_amount": str(authorization.approved_amount)}, commit=False)
    db.commit()
    db.refresh(authorization)
    return authorization
