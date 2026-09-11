from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.encounters.schemas import EncounterResponse


class VitalCreate(BaseModel):
    systolic_bp: int | None = Field(default=None, ge=40, le=300)
    diastolic_bp: int | None = Field(default=None, ge=20, le=200)
    pulse: int | None = Field(default=None, ge=20, le=250)
    temperature_c: float | None = Field(default=None, ge=25, le=45)
    respiratory_rate: int | None = Field(default=None, ge=4, le=80)
    oxygen_saturation: float | None = Field(default=None, ge=50, le=100)
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    height_cm: float | None = Field(default=None, gt=20, le=300)


class VitalResponse(VitalCreate):
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
    diagnosis_name: str = Field(min_length=2, max_length=250)
    diagnosis_type: str = Field(default="PRIMARY", min_length=2, max_length=30)


class DiagnosisResponse(DiagnosisCreate):
    id: UUID
    encounter_id: UUID
    status: str
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
    lab_orders: list[LabOrderSummary] = []
    prescriptions: list[PrescriptionSummary] = []
