"""Schemas for Identity Confidence Engine and membership."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class IdentityProbe(BaseModel):
    """Attributes used to search for existing persons — never store raw ID in logs."""

    national_id_number: str | None = Field(default=None, min_length=7, max_length=9)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    phone: str | None = Field(default=None, max_length=30)
    afya_id: str | None = Field(default=None, max_length=20)
    membership_number: str | None = Field(default=None, max_length=100)


class MatchEvidence(BaseModel):
    code: str
    weight: int
    detail: str


class IdentityCandidate(BaseModel):
    person_id: UUID
    afya_id: str | None
    first_name: str
    last_name: str
    date_of_birth: date | None
    status: str
    score: int
    confidence: str  # HIGH | MEDIUM | LOW
    evidence: list[MatchEvidence]


class IdentityMatchResponse(BaseModel):
    outcome: str  # CLEAR | REVIEW | BLOCK
    top_score: int
    candidates: list[IdentityCandidate]
    guidance: str
    allow_create: bool


class HouseholdCreate(BaseModel):
    head_person_id: UUID
    label: str | None = Field(default=None, max_length=200)
    county: str | None = Field(default=None, max_length=100)


class HouseholdMemberAdd(BaseModel):
    person_id: UUID
    relationship_to_head: str = Field(
        pattern="^(HEAD|SPOUSE|CHILD|PARENT|DEPENDANT|OTHER)$"
    )
    is_dependant: bool = False
    effective_from: date | None = None


class HouseholdResponse(BaseModel):
    id: UUID
    head_person_id: UUID
    label: str | None
    county: str | None
    status: str
    member_count: int


class MembershipCreate(BaseModel):
    person_id: UUID
    payer_id: UUID | None = None
    membership_number: str | None = Field(default=None, max_length=100)
    scheme_code: str | None = Field(default=None, max_length=80)
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|SUSPENDED|LAPSED|TRANSFERRED|CANCELLED)$")
    effective_from: date | None = None
    effective_to: date | None = None
    employer_name: str | None = Field(default=None, max_length=200)
    employer_pin: str | None = Field(default=None, max_length=50)


class MembershipResponse(BaseModel):
    id: UUID
    person_id: UUID
    payer_id: UUID | None
    membership_number: str | None
    status: str
    scheme_code: str | None
    employer_name: str | None
    effective_from: date | None
    effective_to: date | None


class ContributionCreate(BaseModel):
    membership_id: UUID
    period_label: str = Field(min_length=4, max_length=40)
    amount: Decimal = Field(gt=0, le=Decimal("100000000"))
    currency: str = Field(default="KES", min_length=3, max_length=3)
    paid_on: date | None = None
    source: str = Field(default="MANUAL", max_length=40)


class DeceasedMarkRequest(BaseModel):
    person_id: UUID
    date_of_death: date
    reason: str = Field(min_length=5, max_length=500)

    @field_validator("date_of_death")
    @classmethod
    def not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("DEATH_DATE_IN_FUTURE")
        return v


class IdentityCorrectionCreate(BaseModel):
    person_id: UUID
    field_name: str = Field(
        pattern="^(first_name|middle_name|last_name|phone|email|date_of_birth|sex|address)$"
    )
    new_value: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=10, max_length=1000)


class IdentityCorrectionReview(BaseModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    review_notes: str | None = Field(default=None, max_length=500)


class HouseholdListItem(BaseModel):
    id: UUID
    head_person_id: UUID
    head_name: str
    head_afya_id: str | None
    label: str | None
    county: str | None
    status: str
    member_count: int


class HouseholdMemberResponse(BaseModel):
    id: UUID
    person_id: UUID
    afya_id: str | None
    name: str
    phone: str | None
    status: str
    relationship_to_head: str
    is_dependant: bool
    effective_from: date | None
    memberships: list[MembershipResponse]


class HouseholdDetailResponse(BaseModel):
    id: UUID
    head_person_id: UUID
    label: str | None
    county: str | None
    status: str
    member_count: int
    members: list[HouseholdMemberResponse]
