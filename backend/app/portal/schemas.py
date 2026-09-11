from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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
