from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class ContributionRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    reference: str | None = Field(default=None, max_length=150)
    source_type: str = Field(default="MANUAL", max_length=50)
    description: str | None = Field(default=None, max_length=500)


class ApplyRequest(BaseModel):
    invoice_id: UUID
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    reference: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=500)


class WalletTransactionOut(BaseModel):
    id: UUID
    transaction_type: str
    direction: str
    amount: Decimal
    currency: str
    reference: str
    description: str | None
    source_type: str
    source_id: str | None
    invoice_id: UUID | None
    payer_id: UUID | None
    created_at: str


class WalletSummary(BaseModel):
    person_id: UUID
    wallet_id: UUID
    currency: str
    status: str
    available_balance: Decimal
    total_contributions: Decimal
    total_applied: Decimal
    pending_patient_responsibility: Decimal
    transaction_count: int
    transactions: list[WalletTransactionOut]
