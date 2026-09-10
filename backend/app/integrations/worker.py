from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.adapters import IntegrationAdapter, UnconfiguredAdapter
from app.integrations.models import Integration, IntegrationTransaction


def process_pending_transaction(db: Session, transaction_id, adapter: IntegrationAdapter | None = None) -> IntegrationTransaction:
    transaction = db.get(IntegrationTransaction, transaction_id)
    if transaction is None:
        raise ValueError("TRANSACTION_NOT_FOUND")
    integration = db.get(Integration, transaction.integration_id)
    if integration is None:
        raise ValueError("INTEGRATION_NOT_FOUND")
    if integration.status != "ACTIVE":
        raise ValueError("INTEGRATION_NOT_ACTIVE")
    adapter = adapter or UnconfiguredAdapter()
    transaction.status = "PROCESSING"
    db.flush()
    result = adapter.send({"transaction_id": transaction.transaction_id, "entity_type": transaction.entity_type, "entity_id": str(transaction.entity_id) if transaction.entity_id else None}, transaction.transaction_id)
    transaction.status = result.status
    transaction.attempt_count += 1
    transaction.response_code = result.response_code
    transaction.external_reference = result.external_reference
    transaction.response_data = result.response_data or {}
    db.commit()
    db.refresh(transaction)
    return transaction


def list_retryable_transactions(db: Session, limit: int = 100) -> list[IntegrationTransaction]:
    return list(db.scalars(select(IntegrationTransaction).where(IntegrationTransaction.status.in_(["PENDING", "RETRYING"])).order_by(IntegrationTransaction.created_at).limit(max(1, min(limit, 500)))))
