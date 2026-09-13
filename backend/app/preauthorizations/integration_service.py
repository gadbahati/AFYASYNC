from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.integrations.models import Integration
from app.integrations.service import IntegrationError, queue_transaction
from app.preauthorizations.models import PreAuthorization


class PreAuthorizationIntegrationError(ValueError):
    pass


def submit_preauthorization(
    db: Session,
    *,
    authorization_id: UUID,
    facility_id: UUID,
    integration_id: UUID,
    actor_user_id: UUID,
) -> dict:
    authorization = db.scalar(
        select(PreAuthorization).where(
            PreAuthorization.id == authorization_id,
            PreAuthorization.facility_id == facility_id,
        )
    )
    if authorization is None:
        raise PreAuthorizationIntegrationError("PREAUTH_NOT_FOUND")
    if authorization.status != "PENDING":
        raise PreAuthorizationIntegrationError("PREAUTH_NOT_SUBMITTABLE")

    integration = db.scalar(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.facility_id == facility_id,
        )
    )
    if integration is None:
        raise PreAuthorizationIntegrationError("INTEGRATION_NOT_FOUND")
    if integration.status != "ACTIVE":
        raise PreAuthorizationIntegrationError("INTEGRATION_NOT_ACTIVE")
    if integration.integration_type.upper() not in {"PAYER", "SHA", "HEALTH_PAYER"}:
        raise PreAuthorizationIntegrationError("INVALID_PAYER_INTEGRATION")

    transaction_id = f"PREAUTH:{authorization.id}"
    request_reference = authorization.authorization_number
    try:
        transaction = queue_transaction(
            db,
            facility_id,
            integration_id,
            transaction_id,
            "PREAUTHORIZATION",
            authorization.id,
            "OUTBOUND",
            request_reference,
        )
    except IntegrationError as exc:
        raise PreAuthorizationIntegrationError(str(exc)) from exc

    authorization.status = "SUBMITTED"
    db.flush()
    record_audit(
        db,
        action="SUBMIT_PREAUTHORIZATION",
        resource_type="PREAUTHORIZATION",
        resource_id=str(authorization.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=authorization.patient_id,
        metadata={
            "integration_id": str(integration_id),
            "transaction_id": transaction.transaction_id,
            "request_reference": request_reference,
        },
        commit=False,
    )
    db.commit()
    db.refresh(authorization)
    return {
        "authorization_id": authorization.id,
        "transaction_id": transaction.transaction_id,
        "integration_id": integration_id,
        "status": authorization.status,
        "transaction_status": transaction.status,
        "request_reference": request_reference,
    }
