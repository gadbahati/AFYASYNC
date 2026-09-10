from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EncounterCreate(BaseModel):
    patient_id: UUID
    facility_id: UUID
    department_id: UUID
    encounter_type: str = Field(min_length=2, max_length=30)
    reason: str | None = Field(default=None, max_length=2000)


class EncounterResponse(EncounterCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    encounter_id: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    created_by: UUID
