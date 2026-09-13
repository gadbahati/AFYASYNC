import logging
import os
import time

from app.database import SessionLocal
from app.integrations.worker import list_retryable_transactions, process_pending_transaction

logger = logging.getLogger("afasync.integration_worker")


def _poll_seconds() -> float:
    raw = os.getenv("WORKER_POLL_SECONDS", "5")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError("WORKER_POLL_SECONDS must be numeric") from exc
    if value <= 0:
        raise ValueError("WORKER_POLL_SECONDS must be positive")
    return min(value, 300.0)


def run() -> None:
    poll_seconds = _poll_seconds()
    logger.info("AfyaSync integration worker started; poll interval=%ss", poll_seconds)
    while True:
        processed = 0
        try:
            with SessionLocal() as db:
                transactions = list_retryable_transactions(db, limit=100)
                for transaction in transactions:
                    try:
                        process_pending_transaction(db, transaction.id)
                        processed += 1
                    except Exception:
                        db.rollback()
                        logger.exception("Integration transaction processing failed: %s", transaction.id)
        except Exception:
            logger.exception("Integration worker cycle failed")
        if processed:
            logger.info("Integration worker processed %s transaction(s)", processed)
        time.sleep(poll_seconds)


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    run()
