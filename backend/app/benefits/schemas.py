from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BenefitPackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payer_code: str
    package_code: str
    name: str
    description: str
    status: str
