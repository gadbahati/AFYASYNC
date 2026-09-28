from datetime import datetime
from uuid import UUID
from pydantic import BaseModel,Field
class CoordinationCreate(BaseModel):
 referral_id: UUID
 due_at: datetime|None=None
 notes: str|None=Field(default=None,max_length=5000)
class CoordinationUpdate(BaseModel):
 status: str|None=Field(default=None,pattern="^(OPEN|ACCEPTED|SCHEDULED|HANDED_OFF|COMPLETED|CANCELLED|OVERDUE)$")
 appointment_at: datetime|None=None
 outcome: str|None=Field(default=None,max_length=5000)
 notes: str|None=Field(default=None,max_length=5000)
 evidence: dict|None=None
class CoordinationOut(BaseModel):
 id: UUID; case_number: str; referral_id: UUID; patient_id: UUID; source_facility_id: UUID; destination_facility_id: UUID
 status: str; due_at: datetime|None; accepted_at: datetime|None; appointment_at: datetime|None; handoff_at: datetime|None; closed_at: datetime|None
 outcome: str|None; notes: str|None; evidence: dict|None; created_at: datetime; updated_at: datetime
 model_config={"from_attributes":True}
