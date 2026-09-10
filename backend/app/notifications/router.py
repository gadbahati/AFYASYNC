from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.notifications.schemas import NotificationListResponse, NotificationResponse
from app.notifications.service import NotificationError, list_notifications, mark_notification_read
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
def get_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationListResponse:
    items, unread_count = list_notifications(db, user.id, limit=limit, unread_only=unread_only)
    return NotificationListResponse(items=items, unread_count=unread_count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def read_notification(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    try:
        return mark_notification_read(db, user.id, notification_id)
    except NotificationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
