from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class SafetyIncidentCreate(BaseModel):
    patient_id: UUID | None = None
    encounter_id: UUID | None = None
    category: str = Field(min_length=2, max_length=60)
    severity: str = "LOW"
    event_type: str = "INCIDENT"
    occurred_at: datetime
    location: str | None = None
    description: str = Field(min_length=3)
    immediate_action: str | None = None

class SafetyIncidentUpdate(BaseModel):
    status: str | None = None
    corrective_action: str | None = None
    root_cause: str | None = None

class SafetyIncidentResponse(BaseModel):
    id: UUID
    facility_id: UUID
    patient_id: UUID | None
    encounter_id: UUID | None
    incident_number: str
    category: str
    severity: str
    event_type: str
    occurred_at: datetime
    location: str | None
    description: str
    immediate_action: str | None
    status: str
    reported_by: UUID
    corrective_action: str | None
    root_cause: str | None
    closed_at: datetime | None
    closed_by: UUID | None
    model_config = {"from_attributes": True}
