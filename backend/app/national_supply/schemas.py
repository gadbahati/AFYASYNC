from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NationalSupplyItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facility_id: UUID
    facility_code: str = Field(min_length=1, max_length=32)
    facility_name: str = Field(min_length=1, max_length=200)
    county: str | None = Field(default=None, max_length=100)
    medication_id: UUID
    medication_code: str = Field(min_length=1, max_length=50)
    medication_name: str = Field(min_length=1, max_length=200)
    generic_name: str | None = Field(default=None, max_length=200)
    current_quantity: float = Field(ge=0)
    minimum_quantity: float = Field(ge=0)
    low_stock: bool
    non_expired_batch_quantity: float = Field(ge=0)
    expiring_within_30_days_quantity: float = Field(ge=0)
    next_expiry_date: str | None = Field(default=None, max_length=10)


class NationalSupplyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[NationalSupplyItem] = Field(default_factory=list, max_length=200)
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0, le=10000)
