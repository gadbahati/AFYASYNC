# Phase 105 — Apply benefit-engine amounts to invoices

**Developer:** BAHATI GAD WANGWE

## Capabilities

1. **`POST /api/v1/billing/invoices/{invoice_id}/reprice-benefits`**  
   Recomputes line-level `payer_amount` / `patient_amount` from the Universal Benefits & Tariff Engine.  
   Blocked for `PAID` / `VOID` invoices.

2. **Invoice creation fallback**  
   If legacy `PayerBenefitRule` is missing (`COVERAGE_RULE_NOT_CONFIGURED`), `create_invoice` uses `responsibility_from_benefit_engine` instead of hard-failing.

## Integrity

- Per line: `payer_amount + patient_amount == amount`
- Invoice totals rolled up from lines
- Audit action: `REPRICE_INVOICE_BENEFIT_ENGINE`

## Stack

```
Benefit rules (103)
  → quote / quote-batch
  → claims preflight warnings (104)
  → invoice reprice + create fallback (105)
```

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
