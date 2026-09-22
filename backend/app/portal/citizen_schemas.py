"""Afya Citizen super-portal schemas (National Phase 3)."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    event_id: str
    event_type: str
    occurred_at: datetime | None
    title: str
    summary: str | None = None
    facility_id: UUID | None = None
    resource_type: str | None = None
    resource_id: str | None = None


class TimelineResponse(BaseModel):
    person_id: UUID
    events: list[TimelineEvent]
    total: int


class AccessHistoryItem(BaseModel):
    id: str
    action: str
    resource_type: str | None
    resource_id: str | None
    result: str | None
    facility_id: UUID | None
    actor_user_id: UUID | None
    created_at: datetime | None
    metadata_summary: str | None = None


class AccessHistoryResponse(BaseModel):
    items: list[AccessHistoryItem]
    total: int


class ChargeExplainItem(BaseModel):
    charge_or_invoice_id: str
    kind: str  # CHARGE | INVOICE | PAYMENT
    description: str
    amount: Decimal
    patient_amount: Decimal | None = None
    payer_amount: Decimal | None = None
    status: str | None = None
    occurred_at: datetime | None = None
    explanation: str


class ChargeExplainResponse(BaseModel):
    items: list[ChargeExplainItem]
    total_patient_responsibility: Decimal


class ComplaintCreate(BaseModel):
    category: str = Field(
        pattern="^(THAT_WASNT_ME|WRONG_CHARGE|PRIVACY|ACCESS|CLINICAL|OTHER)$"
    )
    subject: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=20, max_length=4000)
    related_encounter_id: UUID | None = None
    related_claim_ref: str | None = Field(default=None, max_length=100)


class ComplaintItem(BaseModel):
    id: UUID
    category: str
    subject: str
    status: str
    created_at: datetime
    resolution_note: str | None = None


class ComplaintListResponse(BaseModel):
    items: list[ComplaintItem]


class EmergencySummary(BaseModel):
    afya_id: str | None
    full_name: str
    date_of_birth: date | None
    sex: str | None
    blood_type: str | None = None
    allergies: list[str]
    active_medications: list[str]
    critical_conditions: list[str]
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    disclaimer: str


class DocumentItem(BaseModel):
    id: str
    doc_type: str
    title: str
    created_at: datetime | None
    status: str | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentItem]
