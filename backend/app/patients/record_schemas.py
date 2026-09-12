from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PatientRecordSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient: dict[str, Any]
    coverage: list[dict[str, Any]]
    encounters: list[dict[str, Any]]
    laboratory: list[dict[str, Any]]
    prescriptions: list[dict[str, Any]]
    medication_actions: list[dict[str, Any]]
    admissions: list[dict[str, Any]]
    preauthorizations: list[dict[str, Any]]
    billing: dict[str, Any]
    claims: list[dict[str, Any]]
    appointments: list[dict[str, Any]]
    queue_history: list[dict[str, Any]]
    referrals: list[dict[str, Any]]
    transfers: list[dict[str, Any]]
