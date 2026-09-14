from uuid import UUID

from pydantic import BaseModel, Field


class ClaimPreflightResponse(BaseModel):
    invoice_id: UUID
    ready: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    payer_id: UUID | None = None
    coverage_id: UUID | None = None
    payer_amount: float = 0
    patient_amount: float = 0
    item_count: int = 0
