from uuid import UUID

from pydantic import BaseModel, Field


class ClaimPreflightResponse(BaseModel):
    invoice_id: UUID
    ready: bool
    errors: list[str] = Field(default_factory=list, max_length=50)
    warnings: list[str] = Field(default_factory=list, max_length=50)
    payer_id: UUID | None = None
    coverage_id: UUID | None = None
    payer_amount: float = Field(default=0, ge=0, le=100_000_000)
    patient_amount: float = Field(default=0, ge=0, le=100_000_000)
    item_count: int = Field(default=0, ge=0, le=10_000)
