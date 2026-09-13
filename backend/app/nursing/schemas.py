from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NursingObservationCreate(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    temperature: str | None = None
    heart_rate: str | None = None
    respiratory_rate: str | None = None
    systolic_bp: str | None = None
    diastolic_bp: str | None = None
    oxygen_saturation: str | None = None
    pain_score: int | None = Field(default=None, ge=0, le=10)
    notes: str | None = None


class NursingNoteCreate(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    shift: str | None = Field(default=None, max_length=30)
    note_type: str = Field(default="PROGRESS", max_length=40)
    content: str = Field(min_length=1)


class NursingHandoverCreate(BaseModel):
    patient_id: UUID
    from_shift: str = Field(max_length=30)
    to_shift: str = Field(max_length=30)
    received_by: UUID | None = None
    summary: str = Field(min_length=1)


class NursingRecordResponse(BaseModel):
    id: UUID
    patient_id: UUID
    facility_id: UUID
    encounter_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
