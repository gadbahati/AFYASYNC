from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ClaimStatusSummary(BaseModel):
    status: str
    count: int
    amount: Decimal
    approved_amount: Decimal
    paid_amount: Decimal


class PayerClaimSummary(BaseModel):
    payer_id: str
    payer_name: str
    payer_code: str
    claims: int
    amount: Decimal
    approved_amount: Decimal
    paid_amount: Decimal
    receivable: Decimal


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
    claims_receivable: Decimal
    claim_statuses: list[ClaimStatusSummary]
    payer_claims: list[PayerClaimSummary]
