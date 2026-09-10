from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AppointmentCreate(BaseModel):
    patient_id: UUID
    facility_id: UUID
    department_id: UUID
    provider_id: UUID | None = None
    appointment_at: datetime
    reason: str | None = Field(default=None, max_length=2000)


class AppointmentResponse(AppointmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str


class QueueCreate(BaseModel):
    facility_id: UUID
    department_id: UUID
    name: str = Field(min_length=2, max_length=150)


class QueueResponse(QueueCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str


class QueueEntryCreate(BaseModel):
    queue_id: UUID
    patient_id: UUID
    appointment_id: UUID | None = None
    priority: str = Field(default="NORMAL", pattern="^(NORMAL|URGENT|EMERGENCY)$")


class QueueEntryResponse(QueueEntryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    encounter_id: UUID | None
    status: str
    queued_at: datetime
    called_at: datetime | None
    completed_at: datetime | None
