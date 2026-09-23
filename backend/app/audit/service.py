from uuid import UUID
import logging

from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.security.privacy import redact_sensitive

logger = logging.getLogger("afyasync.audit")


def record_audit(
    db: Session,
    *,
    action: str,
    resource_type: str,
    result: str,
    user_id: UUID | None = None,
    facility_id: UUID | None = None,
    patient_id: UUID | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    device_id: str | None = None,
    metadata: dict | None = None,
    commit: bool = True,
) -> AuditLog | None:
    """Best-effort audit write — must not break the calling transaction path.

    When commit=False, caller owns the transaction; failures are logged and ignored
    so DR/change-control/risk flows still complete.
    """
    try:
        entry = AuditLog(
            user_id=user_id,
            facility_id=facility_id,
            patient_id=patient_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            ip_address=ip_address,
            device_id=device_id,
            metadata_json=redact_sensitive(metadata or {}),
        )
        db.add(entry)
        if commit:
            db.commit()
            db.refresh(entry)
        return entry
    except Exception:
        logger.exception(
            "audit_write_failed action=%s resource_type=%s resource_id=%s",
            action,
            resource_type,
            resource_id,
        )
        if commit:
            try:
                db.rollback()
            except Exception:
                pass
        return None
