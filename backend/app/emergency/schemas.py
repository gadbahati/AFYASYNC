from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EmergencyVisitCreate(BaseModel):
    patient_id: UUID
    arrival_mode: str | None = Field(default=None, max_length=40)
    chief_complaint: str | None = None
    triage_level: str = Field(default="URGENT", max_length=20)
    notes: str | None = None


class EmergencyTriageCreate(BaseModel):
    temperature: str | None = None
    heart_rate: str | None = None
    respiratory_rate: str | None = None
    systolic_bp: str | None = None
    diastolic_bp: str | None = None
    oxygen_saturation: str | None = None
    pain_score: int | None = Field(default=None, ge=0, le=10)
    consciousness: str | None = Field(default=None, max_length=40)
    notes: str | None = None


class EmergencyDisposition(BaseModel):
    disposition: str = Field(max_length=40)
    notes: str | None = None


class EmergencyVisitResponse(BaseModel):
    id: UUID
    visit_number: str
    patient_id: UUID
    facility_id: UUID
    encounter_id: UUID | None
    arrival_mode: str | None
    chief_complaint: str | None
    triage_level: str
    status: str
    disposition: str | None
    arrived_at: datetime
    seen_at: datetime | None
    closed_at: datetime | None

    model_config = {"from_attributes": True}
