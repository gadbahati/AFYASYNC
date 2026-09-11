from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.integrations.service import queue_transaction


def test_queue_transaction_does_not_commit_by_default() -> None:
    facility_id = uuid4()
    integration_id = uuid4()
    db = MagicMock()
    db.scalar.side_effect = [
        SimpleNamespace(id=integration_id, facility_id=facility_id, status="ACTIVE"),
        None,
    ]

    transaction = queue_transaction(
        db,
        facility_id,
        integration_id,
        "CLM-ATOMIC-1",
        "CLAIM",
        uuid4(),
        "OUTBOUND",
        "CLM-ATOMIC-1",
    )

    assert transaction.status == "PENDING"
    db.flush.assert_called_once()
    db.commit.assert_not_called()


def test_queue_transaction_can_commit_for_direct_callers() -> None:
    facility_id = uuid4()
    integration_id = uuid4()
    db = MagicMock()
    db.scalar.side_effect = [
        SimpleNamespace(id=integration_id, facility_id=facility_id, status="ACTIVE"),
        None,
    ]

    transaction = queue_transaction(
        db,
        facility_id,
        integration_id,
        "TXN-DIRECT-1",
        "PAYMENT",
        uuid4(),
        "OUTBOUND",
        "TXN-DIRECT-1",
        commit=True,
    )

    assert transaction.status == "PENDING"
    db.flush.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(transaction)
