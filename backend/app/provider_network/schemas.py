from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field

class MembershipCreate(BaseModel):
    facility_id: UUID
    network_code: str = Field(min_length=2,max_length=80)
    network_name: str = Field(min_length=2,max_length=200)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    credential_status: str = Field(default="PENDING",max_length=30)
    referral_enabled: bool = True
    claims_enabled: bool = True

class MembershipStatusUpdate(BaseModel):
    status: str = Field(min_length=2,max_length=30)

class MembershipVerificationUpdate(BaseModel):
    verification_type: str = Field(pattern="^(LICENSE|CREDENTIAL|SERVICE)$")
    notes: str | None = Field(default=None, max_length=2000)

class ServiceCreate(BaseModel):
    facility_id: UUID
    network_code: str = Field(min_length=2,max_length=80)
    service_code: str = Field(min_length=2,max_length=80)
    service_name: str = Field(min_length=2,max_length=200)
    department_code: str | None = Field(default=None,max_length=50)
    tariff_amount: Decimal | None = Field(default=None,ge=0,max_digits=14,decimal_places=2)
    referral_required: bool = False

class ContractCreate(BaseModel):
    facility_id: UUID
    network_code: str = Field(min_length=2,max_length=80)
    contract_reference: str = Field(min_length=3,max_length=120)
    payment_terms_days: int = Field(default=30,ge=0,le=365)
    notes: str | None = Field(default=None,max_length=2000)
    effective_from: datetime | None = None
    effective_to: datetime | None = None

class ContractStatusUpdate(BaseModel):
    status: str = Field(min_length=2,max_length=30)

class ContractAcceptance(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)

class ContractNegotiation(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)

class ContractRenewal(BaseModel):
    effective_to: datetime
    renewal_due_at: datetime | None = None

class ContractEventOut(BaseModel):
    id: UUID
    contract_id: UUID
    event_type: str
    from_status: str | None
    to_status: str | None
    actor_id: UUID | None
    notes: str | None
    metadata: dict | None
    created_at: datetime
    model_config = {"from_attributes": True}
