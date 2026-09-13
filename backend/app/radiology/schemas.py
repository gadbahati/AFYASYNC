from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class ImagingTestCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    modality: str = Field(min_length=1, max_length=50)
    description: str | None = None
    price: float = Field(ge=0)

class ImagingOrderCreate(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    test_id: UUID
    clinical_indication: str | None = None

class ImagingReportCreate(BaseModel):
    findings: str = Field(min_length=1)
    impression: str | None = None

class ImagingTestResponse(BaseModel):
    id: UUID; facility_id: UUID; code: str; name: str; modality: str; description: str | None; price: float; active: bool
    model_config = {"from_attributes": True}

class ImagingOrderResponse(BaseModel):
    id: UUID; order_number: str; patient_id: UUID; facility_id: UUID; encounter_id: UUID | None; test_id: UUID; ordered_by: UUID; clinical_indication: str | None; status: str; ordered_at: datetime; completed_at: datetime | None
    model_config = {"from_attributes": True}

class ImagingReportResponse(BaseModel):
    id: UUID; order_id: UUID; performed_by: UUID | None; findings: str; impression: str | None; reported_at: datetime
    model_config = {"from_attributes": True}
