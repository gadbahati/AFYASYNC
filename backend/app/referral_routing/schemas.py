from pydantic import BaseModel,Field
class RoutingRequest(BaseModel):
 service_code: str = Field(min_length=1,max_length=80)
 county: str|None = Field(default=None,max_length=100)
 network_code: str|None = Field(default=None,max_length=80)
 day: str|None = None
 limit: int = Field(default=20,ge=1,le=50)
class RoutingOption(BaseModel):
 facility_id: str
 facility_code: str
 facility_name: str
 county: str|None
 network_code: str
 service_code: str
 service_name: str
 department: str|None
 department_id: str|None
 date: str
 remaining: int
 daily_capacity: int
 booked: int
 slot_minutes: int|None
 referral_required: bool
 tariff_amount: str|None
 currency: str
 route_reason: list[str]
class RoutingResponse(BaseModel):
 service_code: str
 date: str
 options: list[RoutingOption]
