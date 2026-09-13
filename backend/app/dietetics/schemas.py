from uuid import UUID
from pydantic import BaseModel, Field

class NutritionAssessmentCreate(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    weight: str | None = None
    height: str | None = None
    bmi: float | None = Field(default=None, ge=0)
    nutrition_risk: str = "LOW"
    dietary_requirements: str | None = None
    allergies: str | None = None
    notes: str | None = None

class DietOrderCreate(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    diet_type: str = Field(min_length=1, max_length=80)
    texture: str | None = None
    calories: str | None = None
    restrictions: str | None = None
    instructions: str | None = None

class NutritionAssessmentResponse(NutritionAssessmentCreate):
    id: UUID; facility_id: UUID; assessed_by: UUID
    model_config={"from_attributes":True}
class DietOrderResponse(DietOrderCreate):
    id: UUID; facility_id: UUID; status: str; ordered_by: UUID
    model_config={"from_attributes":True}
