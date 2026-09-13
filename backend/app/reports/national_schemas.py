from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class NationalClaimStatusSummary(BaseModel):
    status: str
    count: int
    amount: Decimal
    approved_amount: Decimal
    paid_amount: Decimal


class NationalPayerSummary(BaseModel):
    payer_id: UUID
    payer_name: str
    payer_code: str
    claims: int
    amount: Decimal
    approved_amount: Decimal
    paid_amount: Decimal
    receivable: Decimal


class NationalFacilitySummary(BaseModel):
    facility_id: UUID
    facility_code: str
    facility_name: str
    county: str | None
    encounters: int
    invoices: int
    billed: Decimal
    confirmed_payments: Decimal
    claims: int
    claims_amount: Decimal
    claims_approved: Decimal
    claims_paid: Decimal
    claims_receivable: Decimal


class NationalReport(BaseModel):
    start_date: date
    end_date: date
    active_facilities: int
    registered_patients: int
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
    claims_receivable: Decimal
    claim_statuses: list[NationalClaimStatusSummary]
    payer_claims: list[NationalPayerSummary]
    facilities: list[NationalFacilitySummary]
