from uuid import UUID
from pydantic import BaseModel, Field
class ExchangeMessageCreate(BaseModel):
    message_id: str=Field(min_length=3,max_length=100)
    message_type: str=Field(min_length=2,max_length=60)
    patient_id: UUID|None=None
    source_facility_id: UUID|None=None
    destination_facility_id: UUID|None=None
    correlation_id: str|None=Field(default=None,max_length=100)
    schema_version: str=Field(default="1.0",max_length=30)
    payload: dict=Field(default_factory=dict)
class ExchangeStatusUpdate(BaseModel):
    status: str=Field(min_length=2,max_length=30)
