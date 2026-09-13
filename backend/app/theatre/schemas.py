from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class ProcedureCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None

class BookingCreate(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    procedure_id: UUID
    scheduled_at: datetime
    surgeon_id: UUID | None = None
    anaesthetist_id: UUID | None = None
    indication: str | None = None

class TheatreRecordCreate(BaseModel):
    anaesthesia_type: str | None = None
    preoperative_notes: str | None = None
    procedure_notes: str = Field(min_length=1)
    postoperative_notes: str | None = None
    complications: str | None = None
    outcome: str | None = None

class ProcedureResponse(BaseModel):
    id: UUID; facility_id: UUID; code: str; name: str; description: str | None; status: str
    model_config = {"from_attributes": True}

class BookingResponse(BaseModel):
    id: UUID; patient_id: UUID; facility_id: UUID; encounter_id: UUID | None; procedure_id: UUID; surgeon_id: UUID | None; anaesthetist_id: UUID | None; scheduled_at: datetime; status: str; indication: str | None
    model_config = {"from_attributes": True}

class TheatreRecordResponse(BaseModel):
    id: UUID; booking_id: UUID; anaesthesia_type: str | None; preoperative_notes: str | None; procedure_notes: str; postoperative_notes: str | None; complications: str | None; outcome: str | None; recorded_by: UUID; completed_at: datetime
    model_config = {"from_attributes": True}
