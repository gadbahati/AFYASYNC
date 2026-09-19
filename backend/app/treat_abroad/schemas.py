"""Schemas for SHA Treat Abroad workflows."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApprovedProcedureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None = None
    justification: str | None = None
    max_cover_kes: float
    is_active: bool


class OverseasCaseCreate(BaseModel):
    patient_id: UUID
    facility_id: UUID
    encounter_id: UUID | None = None
    procedure_id: UUID
    clinical_summary: str = Field(min_length=20)
    local_unavailability_reason: str = Field(min_length=10)
    referring_clinician_id: UUID
    foreign_hospital_name: str | None = None
    foreign_hospital_country: str | None = None
    foreign_hospital_city: str | None = None
    planned_departure_date: date | None = None


class OverseasCaseUpdate(BaseModel):
    status: str | None = Field(
        default=None,
        pattern=(
            "^(DRAFT|SUBMITTED|UNDER_REVIEW|APPROVED|REJECTED|"
            "TRAVEL_ARRANGED|TREATMENT_IN_PROGRESS|RETURNED|CLOSED)$"
        ),
    )
    sha_preauth_reference: str | None = None
    sha_commitment_letter_ref: str | None = None
    approved_amount_kes: float | None = None
    sha_decision_notes: str | None = None
    foreign_hospital_name: str | None = None
    foreign_hospital_country: str | None = None
    foreign_hospital_city: str | None = None
    planned_departure_date: date | None = None
    actual_departure_date: date | None = None
    treatment_start_date: date | None = None
    treatment_end_date: date | None = None
    return_date: date | None = None
    follow_up_facility_id: UUID | None = None
    follow_up_notes: str | None = None


class OverseasCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_number: str
    patient_id: UUID
    facility_id: UUID
    encounter_id: UUID | None = None
    procedure_id: UUID
    clinical_summary: str
    local_unavailability_reason: str
    referring_clinician_id: UUID
    status: str
    sha_preauth_reference: str | None = None
    sha_commitment_letter_ref: str | None = None
    approved_amount_kes: float | None = None
    sha_decision_notes: str | None = None
    sha_decided_at: datetime | None = None
    foreign_hospital_name: str | None = None
    foreign_hospital_country: str | None = None
    foreign_hospital_city: str | None = None
    planned_departure_date: date | None = None
    actual_departure_date: date | None = None
    treatment_start_date: date | None = None
    treatment_end_date: date | None = None
    return_date: date | None = None
    follow_up_facility_id: UUID | None = None
    follow_up_notes: str | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
