"""Schemas for patient-controlled sensitive disease disclosure."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SensitiveCategoryOut(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class SensitiveDiseaseConsentCreate(BaseModel):
    """Payload when clinician + patient complete the on-screen consent."""

    diagnosis_id: UUID
    patient_id: UUID
    facility_id: UUID
    encounter_id: UUID | None = None
    consent_given: bool = Field(..., description="True = allow cross-facility sharing")
    sensitive_category_id: UUID | None = None
    signature_data: str | None = Field(
        None, description="Base64-encoded signature image or equivalent proof"
    )
    signature_method: str | None = Field(
        None, description="ON_SCREEN_DRAW | TYPED_NAME | BIOMETRIC"
    )
    device_id: str | None = None
    notes: str | None = None


class SensitiveDiseaseConsentOut(BaseModel):
    id: UUID
    patient_id: UUID
    diagnosis_id: UUID
    facility_id: UUID
    encounter_id: UUID | None = None
    consent_given: bool
    share_scope: str
    sensitive_category_id: UUID | None = None
    signature_method: str | None = None
    recorded_by: UUID
    consented_at: datetime
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConsentCheckResult(BaseModel):
    """Used when deciding whether a diagnosis may be shown across facilities."""

    diagnosis_id: UUID
    patient_id: UUID
    may_share_across_facilities: bool
    consent_given: bool | None = None
    share_scope: str | None = None
    reason: str
