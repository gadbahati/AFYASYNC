from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.claims.service import ClaimsError, build_claim_submission_payload
from app.integrations.adapters import IntegrationAdapter, UnconfiguredAdapter
from app.integrations.models import Integration, IntegrationTransaction

MAX_INTEGRATION_ATTEMPTS = 5


def process_pending_transaction(db: Session, transaction_id, adapter: IntegrationAdapter | None = None) -> IntegrationTransaction:
    transaction = db.get(IntegrationTransaction, transaction_id)
    if transaction is None:
        raise ValueError("TRANSACTION_NOT_FOUND")
    integration = db.get(Integration, transaction.integration_id)
    if integration is None:
        raise ValueError("INTEGRATION_NOT_FOUND")
    if integration.status != "ACTIVE":
        raise ValueError("INTEGRATION_NOT_ACTIVE")
    if transaction.status not in {"PENDING", "RETRYING"}:
        return transaction
    if transaction.attempt_count >= MAX_INTEGRATION_ATTEMPTS:
        transaction.status = "FAILED"
        transaction.response_code = "MAX_ATTEMPTS_EXCEEDED"
        transaction.response_data = {"max_attempts": MAX_INTEGRATION_ATTEMPTS}
        db.commit()
        db.refresh(transaction)
        return transaction

    adapter = adapter or UnconfiguredAdapter()
    transaction.status = "PROCESSING"
    db.flush()

    if transaction.entity_type == "CLAIM":
        if transaction.entity_id is None:
            transaction.status = "FAILED"
            transaction.response_code = "CLAIM_REFERENCE_REQUIRED"
            transaction.response_data = {}
            db.commit()
            db.refresh(transaction)
            return transaction
        try:
            payload = build_claim_submission_payload(db, transaction.entity_id, integration.facility_id)
        except ClaimsError as exc:
            transaction.status = "FAILED"
            transaction.response_code = str(exc)
            transaction.response_data = {}
            db.commit()
            db.refresh(transaction)
            return transaction
    else:
        payload = {
            "transaction_id": transaction.transaction_id,
            "entity_type": transaction.entity_type,
            "entity_id": str(transaction.entity_id) if transaction.entity_id else None,
        }

    try:
        result = adapter.send(payload, transaction.transaction_id)
    except Exception as exc:
        transaction.status = "RETRYING" if transaction.attempt_count + 1 < MAX_INTEGRATION_ATTEMPTS else "FAILED"
        transaction.response_code = "ADAPTER_EXCEPTION"
        transaction.response_data = {"error_type": type(exc).__name__}
        transaction.attempt_count += 1
        transaction.last_attempt_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(transaction)
        return transaction

    if result.status not in {"SUCCEEDED", "FAILED", "RETRYING", "PENDING", "PROCESSING"}:
        transaction.status = "FAILED"
        transaction.response_code = "INVALID_ADAPTER_STATUS"
        transaction.response_data = {}
    else:
        transaction.status = result.status
        transaction.response_code = result.response_code
        transaction.external_reference = result.external_reference
        transaction.response_data = result.response_data or {}
    transaction.attempt_count += 1
    transaction.last_attempt_at = datetime.now(timezone.utc)
    if transaction.status in {"PENDING", "PROCESSING"} and transaction.attempt_count >= MAX_INTEGRATION_ATTEMPTS:
        transaction.status = "FAILED"
        transaction.response_code = "MAX_ATTEMPTS_EXCEEDED"
        transaction.response_data = {"max_attempts": MAX_INTEGRATION_ATTEMPTS}
    db.commit()
    db.refresh(transaction)
    return transaction


def list_retryable_transactions(db: Session, limit: int = 100) -> list[IntegrationTransaction]:
    return list(
        db.scalars(
            select(IntegrationTransaction)
            .where(
                IntegrationTransaction.status.in_(["PENDING", "RETRYING"]),
                IntegrationTransaction.attempt_count < MAX_INTEGRATION_ATTEMPTS,
            )
            .order_by(IntegrationTransaction.created_at)
            .limit(max(1, min(limit, 500)))
        )
    )
