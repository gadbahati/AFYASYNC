from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, Field

class PregnancyCreate(BaseModel):
    patient_id: UUID
    gravida: int | None = Field(default=None, ge=0)
    para: int | None = Field(default=None, ge=0)
    lmp: date | None = None
    estimated_due_date: date | None = None
    gestational_age_weeks: int | None = Field(default=None, ge=0, le=45)
    risk_level: str = "ROUTINE"

class AntenatalVisitCreate(BaseModel):
    gestational_age_weeks: int | None = Field(default=None, ge=0, le=45)
    blood_pressure: str | None = None
    weight: str | None = None
    fetal_heart_rate: str | None = None
    findings: str | None = None
    plan: str | None = None

class DeliveryCreate(BaseModel):
    delivery_datetime: datetime
    mode: str = Field(min_length=1, max_length=40)
    outcome: str = Field(min_length=1, max_length=40)
    newborn_count: int = Field(default=1, ge=1, le=10)
    complications: str | None = None
    notes: str | None = None

class NewbornCreate(BaseModel):
    sex: str | None = None
    birth_weight: str | None = None
    apgar_1: int | None = Field(default=None, ge=0, le=10)
    apgar_5: int | None = Field(default=None, ge=0, le=10)
    notes: str | None = None

class PregnancyResponse(BaseModel):
    id: UUID; patient_id: UUID; facility_id: UUID; gravida: int | None; para: int | None; lmp: date | None; estimated_due_date: date | None; gestational_age_weeks: int | None; risk_level: str; status: str
    model_config={"from_attributes":True}

class AntenatalVisitResponse(BaseModel):
    id: UUID; pregnancy_id: UUID; patient_id: UUID; facility_id: UUID; clinician_id: UUID; visit_date: datetime; gestational_age_weeks: int | None; blood_pressure: str | None; weight: str | None; fetal_heart_rate: str | None; findings: str | None; plan: str | None
    model_config={"from_attributes":True}

class DeliveryResponse(BaseModel):
    id: UUID; pregnancy_id: UUID; mother_id: UUID; facility_id: UUID; delivery_datetime: datetime; mode: str; outcome: str; newborn_count: int; complications: str | None; notes: str | None
    model_config={"from_attributes":True}

class NewbornResponse(BaseModel):
    id: UUID; delivery_id: UUID; mother_id: UUID; patient_id: UUID | None; facility_id: UUID; sex: str | None; birth_weight: str | None; apgar_1: int | None; apgar_5: int | None; status: str; notes: str | None
    model_config={"from_attributes":True}
