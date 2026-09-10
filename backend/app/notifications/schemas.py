from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notification_type: str
    title: str
    message: str
    priority: str
    action_url: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int


class NotificationCreate(BaseModel):
    user_id: UUID | None = None
    person_id: UUID | None = None
    facility_id: UUID | None = None
    notification_type: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)
    priority: str = Field(default="NORMAL", pattern="^(LOW|NORMAL|HIGH|URGENT)$")
    action_url: str | None = Field(default=None, max_length=500)
    metadata: dict = Field(default_factory=dict)
