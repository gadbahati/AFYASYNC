from pydantic import BaseModel, Field


class CrossFacilityRecordResponse(BaseModel):
    patient_id: str
    access_reason: str
    source_facility_count: int
    records: list[dict]


class CrossFacilityMPIResponse(BaseModel):
    candidates: list[dict]
    requires_review_before_access: bool
