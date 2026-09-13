from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class WardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    ward_type: str = Field(default="GENERAL", max_length=50)

class BedCreate(BaseModel):
    ward_id: UUID
    bed_number: str = Field(min_length=1, max_length=50)

class BedAssign(BaseModel):
    admission_id: UUID

class WardResponse(BaseModel):
    id: UUID
    facility_id: UUID
    name: str
    ward_type: str
    status: str
    model_config = {"from_attributes": True}

class BedResponse(BaseModel):
    id: UUID
    ward_id: UUID
    bed_number: str
    status: str
    model_config = {"from_attributes": True}

class BedAssignmentResponse(BaseModel):
    id: UUID
    bed_id: UUID
    admission_id: UUID
    assigned_by: UUID
    assigned_at: datetime
    released_at: datetime | None
    model_config = {"from_attributes": True}
