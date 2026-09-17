from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.encounters.schemas import EncounterResponse


class VitalCreate(BaseModel):
    systolic_bp: int | None = Field(default=None, ge=50, le=300)
    diastolic_bp: int | None = Field(default=None, ge=20, le=200)
    pulse: int | None = Field(default=None, ge=20, le=250)
    temperature_c: float | None = Field(default=None, ge=25, le=45)
    respiratory_rate: int | None = Field(default=None, ge=5, le=80)
    oxygen_saturation: float | None = Field(default=None, ge=50, le=100)
    weight_kg: float | None = Field(default=None, ge=0.1, le=500)
    height_cm: float | None = Field(default=None, ge=20, le=250)


class VitalResponse(VitalCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    encounter_id: UUID
    recorded_by: UUID
    bmi: float | None
    recorded_at: datetime


class ConsultationCreate(BaseModel):
    chief_complaint: str | None = None
    history: str | None = None
    examination: str | None = None
    assessment: str | None = None
    clinical_notes: str | None = None
    treatment_plan: str | None = None


class ConsultationResponse(ConsultationCreate):
    id: UUID
    encounter_id: UUID
    doctor_id: UUID
    created_at: datetime
    updated_at: datetime


class DiagnosisCreate(BaseModel):
    diagnosis_code: str | None = None
    diagnosis_name: str = Field(min_length=1, max_length=250)
    diagnosis_type: str = "PRIMARY"
    status: str = "ACTIVE"


class DiagnosisResponse(DiagnosisCreate):
    id: UUID
    encounter_id: UUID
    recorded_by: UUID
    created_at: datetime


class LabOrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_id: str
    encounter_id: UUID
    patient_id: UUID
    priority: str
    status: str
    created_at: datetime


class PrescriptionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    prescription_id: str
    encounter_id: UUID
    patient_id: UUID
    status: str
    created_at: datetime


class ClinicalTimelineSummary(BaseModel):
    encounter: EncounterResponse
    vitals: list[VitalResponse]
    consultation: ConsultationResponse | None
    diagnoses: list[DiagnosisResponse]
    lab_orders: list[LabOrderSummary]
    prescriptions: list[PrescriptionSummary]


class CarePlanCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    goals: str | None = Field(default=None, max_length=10000)
    interventions: str | None = Field(default=None, max_length=10000)
    clinical_notes: str | None = Field(default=None, max_length=10000)
    target_date: date | None = None
    encounter_id: UUID | None = None


class CarePlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    goals: str | None = Field(default=None, max_length=10000)
    interventions: str | None = Field(default=None, max_length=10000)
    clinical_notes: str | None = Field(default=None, max_length=10000)
    target_date: date | None = None
    encounter_id: UUID | None = None
    status: str | None = Field(default=None, pattern="^(ACTIVE|COMPLETED|CANCELLED)$")


class CarePlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    patient_id: UUID
    facility_id: UUID
    encounter_id: UUID | None
    created_by: UUID
    title: str
    goals: str | None
    interventions: str | None
    clinical_notes: str | None
    target_date: date | None
    status: str
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AllergyCreate(BaseModel):
    allergen: str = Field(min_length=1, max_length=200)
    reaction: str | None = Field(default=None, max_length=5000)
    severity: str = Field(default="UNKNOWN", pattern="^(UNKNOWN|MILD|MODERATE|SEVERE|LIFE_THREATENING)$")
    onset_date: date | None = None
    notes: str | None = Field(default=None, max_length=10000)


class AllergyUpdate(BaseModel):
    allergen: str | None = Field(default=None, min_length=1, max_length=200)
    reaction: str | None = Field(default=None, max_length=5000)
    severity: str | None = Field(default=None, pattern="^(UNKNOWN|MILD|MODERATE|SEVERE|LIFE_THREATENING)$")
    status: str | None = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")
    onset_date: date | None = None
    notes: str | None = Field(default=None, max_length=10000)


class AllergyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    patient_id: UUID
    facility_id: UUID
    recorded_by: UUID
    allergen: str
    reaction: str | None
    severity: str
    status: str
    onset_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
