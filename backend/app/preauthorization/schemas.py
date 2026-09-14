from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PreauthorizationCreate(BaseModel):
    patient_id: UUID
    coverage_id: UUID
    service_code: str = Field(min_length=1, max_length=80)
    service_type: str = Field(min_length=1, max_length=60)
    requested_amount: Decimal = Field(gt=0, le=100_000_000, decimal_places=2)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("service_code", "service_type", "reason")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("FIELD_REQUIRED")
        return value


class PreauthorizationResponse(BaseModel):
    id: UUID
    patient_id: UUID
    facility_id: UUID
    coverage_id: UUID
    payer_id: UUID
    service_code: str
    service_type: str
    requested_amount: Decimal
    status: str
    reason: str
    external_reference: str | None
    created_at: datetime
    updated_at: datetime
