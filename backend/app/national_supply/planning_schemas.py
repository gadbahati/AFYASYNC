from uuid import UUID

from pydantic import BaseModel, Field, model_validator


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

    @model_validator(mode="after")
    def validate_transfer_math(self) -> "SupplyReplenishmentRecommendation":
        expected_shortage = self.minimum_quantity - self.current_quantity
        if expected_shortage <= 0:
            raise ValueError("SHORTAGE_MUST_BE_POSITIVE")
        if abs(self.shortage_quantity - expected_shortage) > 1e-6:
            raise ValueError("SHORTAGE_DOES_NOT_MATCH_STOCK_LEVELS")
        if self.suggested_transfer_quantity > self.shortage_quantity + 1e-6:
            raise ValueError("TRANSFER_EXCEEDS_SHORTAGE")
        donor_total = sum(donor.available_surplus for donor in self.donors)
        if abs(donor_total - self.suggested_transfer_quantity) > 1e-6:
            raise ValueError("DONOR_TOTAL_DOES_NOT_MATCH_TRANSFER")
        return self


class SupplyPlanningResponse(BaseModel):
    recommendations: list[SupplyReplenishmentRecommendation] = Field(default_factory=list, max_length=200)
    total_recommendations: int = Field(ge=0, le=200)
    generated_from_live_inventory: bool = True
    input_rows_considered: int = Field(default=0, ge=0, le=50_001)
    input_rows_truncated: bool = False

    @model_validator(mode="after")
    def validate_total(self) -> "SupplyPlanningResponse":
        if self.total_recommendations != len(self.recommendations):
            raise ValueError("TOTAL_RECOMMENDATIONS_MISMATCH")
        if self.input_rows_truncated and self.input_rows_considered <= 50_000:
            raise ValueError("TRUNCATION_FLAG_REQUIRES_INPUT_OVER_LIMIT")
        return self
