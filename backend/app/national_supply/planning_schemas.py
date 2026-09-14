from uuid import UUID

from pydantic import BaseModel, Field


class SupplyDonor(BaseModel):
    facility_id: UUID
    facility_code: str = Field(min_length=1, max_length=32)
    facility_name: str = Field(min_length=1, max_length=200)
    county: str | None = Field(default=None, max_length=100)
    available_surplus: float = Field(ge=0, le=1_000_000)


class SupplyReplenishmentRecommendation(BaseModel):
    facility_id: UUID
    facility_code: str = Field(min_length=1, max_length=32)
    facility_name: str = Field(min_length=1, max_length=200)
    county: str | None = Field(default=None, max_length=100)
    medication_id: UUID
    medication_code: str = Field(min_length=1, max_length=50)
    medication_name: str = Field(min_length=1, max_length=200)
    current_quantity: float = Field(ge=0, le=1_000_000)
    minimum_quantity: float = Field(ge=0, le=1_000_000)
    shortage_quantity: float = Field(gt=0, le=1_000_000)
    suggested_transfer_quantity: float = Field(gt=0, le=1_000_000)
    donors: list[SupplyDonor] = Field(default_factory=list, max_length=10)


class SupplyPlanningResponse(BaseModel):
    recommendations: list[SupplyReplenishmentRecommendation] = Field(default_factory=list, max_length=200)
    total_recommendations: int = Field(ge=0, le=200)
    generated_from_live_inventory: bool = True
