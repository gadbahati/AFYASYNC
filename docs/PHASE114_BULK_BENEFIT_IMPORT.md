# Phase 114 — Bulk benefit / tariff rule import

**Developer:** BAHATI GAD WANGWE

## API

```
POST /api/v1/benefit-engine/rules/import
{
  "stop_on_error": false,
  "rules": [
    {
      "benefit_package_id": "...",
      "payer_id": "...",
      "name": "OP consult",
      "service_code": "CONSULT-OP",
      "tariff_amount": 1500,
      "payer_percent": 100,
      "requires_preauth": false,
      "effective_from": "2026-01-01",
      "status": "ACTIVE"
    }
  ]
}
```

Max 500 rules per request. Returns `created_count`, `errors[]`.

## UI

Benefits & tariff engine page — **Bulk import** JSON textarea.

## Client

`api.importBenefitRules({ rules, stop_on_error })`

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
