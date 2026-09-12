from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class FacilityReport(BaseModel):
    facility_id: str
    start_date: date
    end_date: date
    patients: int
    encounters: int
    charges_total: Decimal
    invoices_total: Decimal
    payer_billed: Decimal
    patient_billed: Decimal
    confirmed_payments: Decimal
    claims: int
    claims_amount: Decimal
    claims_approved: Decimal
    claims_paid: Decimal
