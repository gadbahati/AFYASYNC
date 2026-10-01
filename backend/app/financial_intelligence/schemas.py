from pydantic import BaseModel, Field

class FinancialWindow(BaseModel):
    days: int = Field(default=90, ge=7, le=365)
