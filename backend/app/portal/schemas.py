from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.clinical.schemas import (
    ConsultationResponse,
    DiagnosisResponse,
    LabOrderSummary,
    PrescriptionSummary,
    VitalResponse,
)
from app.encounters.schemas import EncounterResponse
from app.referrals.schemas import ReferralOut


class PortalProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    afya_id: str | None = None
    first_name: str
    middle_name: str | None
    last_name: str
    date_of_birth: date | None
    sex: str | None
    phone: str | None
    email: str | None
    status: str


class PortalEncounterListResponse(BaseModel):
    items: list[EncounterResponse]
    total: int
    limit: int
    offset: int


class PortalEncounterSummary(BaseModel):
    encounter: EncounterResponse
    vitals: list[VitalResponse]
    consultation: ConsultationResponse | None
    diagnoses: list[DiagnosisResponse]
    lab_orders: list[LabOrderSummary] = []
    prescriptions: list[PrescriptionSummary] = []


class PortalReferralListResponse(BaseModel):
    items: list[ReferralOut]
    total: int
    limit: int
    offset: int


class PortalConsentItem(BaseModel):
    """Patient-visible record of a sensitive disease disclosure decision."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    diagnosis_id: UUID
    facility_id: UUID
    consent_given: bool
    share_scope: str
    signature_method: str | None = None
    consented_at: datetime
    notes: str | None = None


class PortalConsentListResponse(BaseModel):
    items: list[PortalConsentItem]
    total: int


class PortalConsentUpdate(BaseModel):
    """Patient request to change a previous disclosure decision."""

    consent_given: bool = Field(..., description="True = allow cross-facility sharing")
    signature_data: str | None = Field(
        None, description="New on-screen signature proof"
    )
    signature_method: str | None = Field(
        None, description="ON_SCREEN_DRAW | TYPED_NAME | BIOMETRIC"
    )
    notes: str | None = None


class PortalCoverageItem(BaseModel):
    id: UUID
    payer_name: str | None = None
    coverage_mode: str | None = None
    membership_number: str | None = None
    status: str | None = None
    verification_status: str | None = None


class PortalCoverageSummary(BaseModel):
    items: list[PortalCoverageItem]
    total: int
