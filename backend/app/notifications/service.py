from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.notifications.models import Notification
from app.rbac.models import User


class NotificationError(ValueError):
    pass


def create_notification(db: Session, payload: dict, *, actor_user_id: UUID | None = None, commit: bool = True) -> Notification:
    if payload.get("user_id") is None and payload.get("person_id") is None:
        raise NotificationError("NOTIFICATION_RECIPIENT_REQUIRED")
    if payload.get("user_id") is not None:
        user = db.get(User, payload["user_id"])
        if user is None or user.status != "ACTIVE":
            raise NotificationError("RECIPIENT_NOT_FOUND")
        if payload.get("person_id") is not None and user.person_id != payload["person_id"]:
            raise NotificationError("RECIPIENT_MISMATCH")
    notification = Notification(
        user_id=payload.get("user_id"),
        person_id=payload.get("person_id"),
        facility_id=payload.get("facility_id"),
        notification_type=payload["notification_type"].upper(),
        title=payload["title"],
        message=payload["message"],
        priority=payload.get("priority", "NORMAL").upper(),
        action_url=payload.get("action_url"),
        metadata_json=payload.get("metadata", {}),
    )
    db.add(notification)
    db.flush()
    if actor_user_id is not None:
        record_audit(db, action="CREATE_NOTIFICATION", resource_type="NOTIFICATION", resource_id=str(notification.id), result="SUCCESS", user_id=actor_user_id, facility_id=notification.facility_id, patient_id=notification.person_id, metadata={"notification_type": notification.notification_type}, commit=False)
    if commit:
        db.commit()
        db.refresh(notification)
    return notification


def list_notifications(db: Session, user_id: UUID, *, limit: int = 50, unread_only: bool = False) -> tuple[list[Notification], int]:
    limit = min(max(limit, 1), 100)
    stmt = select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    items = list(db.scalars(stmt))
    unread_count = int(db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))) or 0)
    return items, unread_count


def mark_notification_read(db: Session, user_id: UUID, notification_id: UUID) -> Notification:
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        raise NotificationError("NOTIFICATION_NOT_FOUND")
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return notification
