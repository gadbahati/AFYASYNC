from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class InfectionIncidentCreate(BaseModel):
    patient_id: UUID | None = None
    encounter_id: UUID | None = None
    incident_type: str = Field(min_length=1, max_length=80)
    suspected_infection: str | None = None
    specimen_collected: str | None = None
    onset_at: datetime | None = None
    severity: str = "MODERATE"
    isolation_required: bool = False
    notes: str | None = None

class IsolationCreate(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    precaution_type: str = Field(min_length=1, max_length=60)
    reason: str | None = None

class InfectionIncidentResponse(BaseModel):
    id: UUID; facility_id: UUID; patient_id: UUID | None; encounter_id: UUID | None; incident_type: str; suspected_infection: str | None; specimen_collected: str | None; onset_at: datetime | None; severity: str; status: str; isolation_required: bool; notes: str | None; reported_by: UUID; created_at: datetime
    model_config={"from_attributes":True}

class IsolationResponse(BaseModel):
    id: UUID; facility_id: UUID; patient_id: UUID; encounter_id: UUID | None; precaution_type: str; reason: str | None; status: str; started_at: datetime; ended_at: datetime | None; created_by: UUID
    model_config={"from_attributes":True}
