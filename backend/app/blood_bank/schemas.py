from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
class BloodUnitCreate(BaseModel):
    donation_number:str=Field(min_length=1,max_length=80); blood_group:str=Field(min_length=2,max_length=5); component:str="WHOLE_BLOOD"; collected_at:datetime|None=None; expires_at:datetime|None=None; screening_status:str="PENDING"; storage_location:str|None=None; notes:str|None=None
class BloodRequestCreate(BaseModel):
    patient_id:UUID; encounter_id:UUID|None=None; blood_group:str|None=None; component:str="WHOLE_BLOOD"; units_requested:int=Field(default=1,ge=1); urgency:str="ROUTINE"; indication:str|None=None
class CrossmatchCreate(BaseModel):
    blood_unit_id:UUID; patient_blood_group:str; result:str; notes:str|None=None
class TransfusionCreate(BaseModel):
    blood_unit_id:UUID; started_at:datetime|None=None; observations:str|None=None
class ReactionCreate(BaseModel):
    reaction_type:str; severity:str; action_taken:str|None=None; outcome:str|None=None
class BloodUnitResponse(BaseModel):
    id:UUID; donation_number:str; blood_group:str; component:str; status:str; screening_status:str; storage_location:str|None; expires_at:datetime|None
    model_config={"from_attributes":True}
class BloodRequestResponse(BaseModel):
    id:UUID; patient_id:UUID; encounter_id:UUID|None; blood_group:str|None; component:str; units_requested:int; urgency:str; status:str
    model_config={"from_attributes":True}
