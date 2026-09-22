"""Can I Get This? — national benefit interrogation schemas."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CanIGetThisRequest(BaseModel):
    person_id: UUID
    service_code: str = Field(min_length=1, max_length=80)
    service_type: str | None = Field(default=None, max_length=60)
    service_name: str | None = Field(default=None, max_length=200)
    quantity: Decimal = Field(default=Decimal("1"), gt=0, le=Decimal("1000"))
    unit_price: Decimal = Field(default=Decimal("0"), ge=0, le=Decimal("100000000"))
    facility_id: UUID | None = None  # optional override; staff context preferred
    as_of: date | None = None  # historical rule reconstruction date


class DocumentRequirement(BaseModel):
    code: str
    description: str


class PayerDecision(BaseModel):
    coverage_id: UUID
    payer_id: UUID
    payer_code: str
    payer_name: str
    membership_number: str | None
    eligibility: str  # ELIGIBLE | EXPIRED | INACTIVE | UNVERIFIED | NOT_YET_ACTIVE | EXCLUDED
    covered: bool
    requires_authorisation: bool
    remaining_benefit: Decimal | None
    annual_limit: Decimal | None
    utilised_ytd: Decimal | None
    expected_payer_amount: Decimal
    expected_patient_amount: Decimal
    rule_id: UUID | None
    rule_version_note: str | None
    coordination_rank: int  # 1 = primary
    messages: list[str]


class CanIGetThisResponse(BaseModel):
    service_code: str
    service_type: str | None
    service_name: str | None
    as_of: date
    line_total: Decimal
    overall_eligible: bool
    overall_covered: bool
    requires_authorisation: bool
    primary_payer_amount: Decimal
    secondary_payer_amount: Decimal
    patient_responsibility: Decimal
    cash_fallback_amount: Decimal
    documents_required: list[DocumentRequirement]
    facility_requirements: list[str]
    payers: list[PayerDecision]
    summary: str
    guidance: list[str]
