from datetime import date
from uuid import UUID
from pydantic import BaseModel, Field, model_validator
class BenefitRuleVersionCreate(BaseModel):
    benefit_package_id: UUID
    payer_id: UUID
    payer_plan_id: UUID | None = None
    name: str = Field(min_length=2,max_length=160)
    version: int = Field(default=1,ge=1)
    service_code: str | None = Field(default=None,max_length=80)
    service_type: str | None = Field(default=None,max_length=60)
    tariff_amount: float | None = Field(default=None,ge=0)
    currency: str = Field(default="KES",min_length=3,max_length=3)
    payer_percent: float = Field(default=100,ge=0,le=100)
    fixed_patient_copay: float = Field(default=0,ge=0)
    max_covered_amount: float | None = Field(default=None,ge=0)
    annual_limit_amount: float | None = Field(default=None,ge=0)
    is_excluded: bool = False
    requires_preauth: bool = False
    effective_from: date
    effective_to: date | None = None
    status: str = Field(default="DRAFT",pattern="^(DRAFT|ACTIVE|RETIRED)$")
    @model_validator(mode="after")
    def validate_rule(self):
        if not self.service_code and not self.service_type: raise ValueError("BENEFIT_SCOPE_REQUIRED")
        if self.effective_to and self.effective_to < self.effective_from: raise ValueError("INVALID_BENEFIT_DATES")
        return self
class BenefitRuleVersionOut(BenefitRuleVersionCreate):
    id: UUID
    model_config={"from_attributes":True}
class BenefitQuoteRequest(BaseModel):
    payer_id: UUID
    payer_plan_id: UUID | None = None
    benefit_package_id: UUID | None = None
    service_code: str | None = None
    service_type: str | None = None
    gross_amount: float = Field(gt=0)
    as_of: date | None = None
    @model_validator(mode="after")
    def scope(self):
        if not self.service_code and not self.service_type: raise ValueError("BENEFIT_SCOPE_REQUIRED")
        return self
class BenefitQuoteResponse(BaseModel):
    matched: bool
    rule_id: UUID | None
    package_id: UUID | None
    version: int | None
    tariff_amount: float | None
    gross_amount: float
    allowed_amount: float
    payer_amount: float
    patient_amount: float
    currency: str
    decision: str
    reason_code: str
    requires_preauth: bool
