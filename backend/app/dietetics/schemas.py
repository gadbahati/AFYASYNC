from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class NutritionAssessmentCreate(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    weight: str | None = Field(default=None, max_length=30)
    height: str | None = Field(default=None, max_length=30)
    bmi: float | None = Field(default=None, ge=0, le=100)
    nutrition_risk: str = Field(default="LOW", min_length=2, max_length=40)
    dietary_requirements: str | None = None
    allergies: str | None = None
    notes: str | None = None

    @field_validator("nutrition_risk")
    @classmethod
    def normalize_risk(cls, value: str) -> str:
        value = value.strip().upper()
        allowed = {"LOW", "MODERATE", "HIGH", "CRITICAL"}
        if value not in allowed:
            raise ValueError("nutrition_risk must be LOW, MODERATE, HIGH, or CRITICAL")
        return value


class DietOrderCreate(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    diet_type: str = Field(min_length=1, max_length=80)
    texture: str | None = Field(default=None, max_length=60)
    calories: str | None = Field(default=None, max_length=40)
    restrictions: str | None = None
    instructions: str | None = None

    @field_validator("diet_type", "texture", "calories", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class NutritionAssessmentResponse(NutritionAssessmentCreate):
    id: UUID
    facility_id: UUID
    assessed_by: UUID
    assessed_at: datetime
    model_config = {"from_attributes": True}


class DietOrderResponse(DietOrderCreate):
    id: UUID
    facility_id: UUID
    status: str
    ordered_by: UUID
    ordered_at: datetime
    model_config = {"from_attributes": True}


class DietOrderStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"ACTIVE", "SUSPENDED", "COMPLETED", "CANCELLED"}:
            raise ValueError("status must be ACTIVE, SUSPENDED, COMPLETED, or CANCELLED")
        return value
