from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.models import AuditLog


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
) -> AuditLog:
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
        metadata_json=metadata or {},
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    return entry
