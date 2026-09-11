from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.notifications.service import create_notification
from app.rbac.models import User


# Event templates intentionally contain minimal, non-clinical content. Detailed
# clinical information must remain inside the authenticated AfyaSync portal.
EVENT_TEMPLATES = {
    "APPOINTMENT_CONFIRMED": ("Appointment confirmed", "Your AfyaSync appointment has been confirmed."),
    "APPOINTMENT_REMINDER": ("Appointment reminder", "You have an upcoming AfyaSync appointment."),
    "QUEUE_CHECKIN": ("Check-in complete", "Your AfyaSync check-in has been recorded."),
    "QUEUE_STATUS_CHANGED": ("Queue status updated", "Your AfyaSync queue status has been updated."),
    "LAB_RESULT_READY": ("Lab result available", "A laboratory result is available in your AfyaSync account."),
    "PRESCRIPTION_READY": ("Prescription update", "A prescription update is available in your AfyaSync account."),
    "BILL_CREATED": ("New bill", "A new bill is available in your AfyaSync account."),
    "PAYMENT_CONFIRMED": ("Payment confirmed", "Your AfyaSync payment has been confirmed."),
    "CLAIM_STATUS_CHANGED": ("Claim status updated", "Your healthcare claim status has been updated."),
    "REFERRAL_CREATED": ("Referral created", "A healthcare referral has been created for you."),
    "REFERRAL_STATUS_CHANGED": ("Referral updated", "Your healthcare referral status has been updated."),
    "TRANSFER_REQUESTED": ("Transfer requested", "A healthcare transfer has been requested for you."),
    "TRANSFER_STATUS_CHANGED": ("Transfer updated", "Your interfacility transfer status has been updated."),
}


def notify_patient_event(
    db: Session,
    *,
    patient_id: UUID,
    event_type: str,
    facility_id: UUID | None = None,
    action_url: str | None = None,
    priority: str = "NORMAL",
    metadata: dict | None = None,
    actor_user_id: UUID | None = None,
    commit: bool = True,
):
    event_type = event_type.upper()
    if event_type not in EVENT_TEMPLATES:
        raise ValueError("UNSUPPORTED_NOTIFICATION_EVENT")

    user = db.scalar(
        select(User)
        .where(User.person_id == patient_id, User.status == "ACTIVE")
        .order_by(User.created_at.asc())
        .limit(1)
    )
    if user is None:
        return None

    title, message = EVENT_TEMPLATES[event_type]
    return create_notification(
        db,
        {
            "user_id": user.id,
            "person_id": patient_id,
            "facility_id": facility_id,
            "notification_type": event_type,
            "title": title,
            "message": message,
            "priority": priority,
            "action_url": action_url,
            "metadata": metadata or {},
        },
        actor_user_id=actor_user_id,
        commit=commit,
    )
