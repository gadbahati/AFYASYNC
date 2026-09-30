from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
class BookingCreate(BaseModel):
    patient_id: UUID
    encounter_id: UUID
    destination_facility_id: UUID
    destination_department_id: UUID
    service_code: str = Field(min_length=1, max_length=80)
    network_code: str = Field(min_length=1, max_length=80)
    appointment_at: datetime
    reason: str = Field(min_length=3, max_length=4000)
    priority: str = Field(default="ROUTINE", pattern="^(ROUTINE|URGENT|EMERGENCY)$")
    clinical_summary: str | None = Field(default=None, max_length=10000)
    notes: str | None = Field(default=None, max_length=5000)
class BookingOut(BaseModel):
    booking_id: UUID
    booking_reference: str
    referral_id: UUID
    appointment_id: UUID
    coordination_case_id: UUID
    status: str
    patient_id: UUID
    source_facility_id: UUID
    destination_facility_id: UUID
    destination_department_id: UUID
    service_code: str
    network_code: str
    appointment_at: datetime
