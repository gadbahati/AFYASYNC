from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, Field

class ChildHealthCreate(BaseModel):
    patient_id: UUID
    mother_id: UUID | None = None
    birth_date: date | None = None
    birth_weight: str | None = None
    notes: str | None = None

class GrowthCreate(BaseModel):
    age_months: int | None = Field(default=None, ge=0, le=216)
    weight: str | None = None
    height: str | None = None
    head_circumference: str | None = None
    assessment: str | None = None

class ImmunisationCreate(BaseModel):
    vaccine: str = Field(min_length=1, max_length=120)
    dose: str = Field(min_length=1, max_length=40)
    next_due_at: datetime | None = None
    batch_number: str | None = None
    notes: str | None = None

class ChildHealthResponse(BaseModel):
    id: UUID; patient_id: UUID; facility_id: UUID; mother_id: UUID | None; birth_date: date | None; birth_weight: str | None; notes: str | None; status: str
    model_config={"from_attributes":True}
class GrowthResponse(BaseModel):
    id: UUID; child_id: UUID; facility_id: UUID; observed_at: datetime; age_months: int | None; weight: str | None; height: str | None; head_circumference: str | None; assessment: str | None
    model_config={"from_attributes":True}
class ImmunisationResponse(BaseModel):
    id: UUID; child_id: UUID; facility_id: UUID; vaccine: str; dose: str; administered_at: datetime; next_due_at: datetime | None; batch_number: str | None; notes: str | None
    model_config={"from_attributes":True}
