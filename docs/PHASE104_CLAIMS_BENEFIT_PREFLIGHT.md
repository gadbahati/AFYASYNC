# Phase 104 — Claims preflight × benefit engine

**Developer:** BAHATI GAD WANGWE

## Goal

Claim readiness must use the same tariff truth as the Benefits & Tariff Engine.

## Flow

```
Invoice lines → service code/type + gross
  → benefit_engine.quote_lines(payer, plan, as_of)
  → errors / warnings on preflight response
```

## Codes

| Code | Severity |
|------|----------|
| `BENEFIT_EXCLUDED:{service}` | **error** — blocks ready |
| `BENEFIT_RULE_MISSING:{service}` | warning |
| `BENEFIT_PREAUTH_REQUIRED:{service}` | warning |
| `BENEFIT_AMOUNT_VARIANCE:...` | warning (>5% and >KES 50 vs invoice) |
| `BENEFIT_ENGINE_UNAVAILABLE` | warning (engine exception) |

## Response extras

- `benefit_unknown_rules`
- `benefit_preauth_lines`
- `benefit_ineligible_lines`
- `benefit_engine_payer_total`
- `benefit_engine_patient_total`

Audit `CLAIM_PREFLIGHT` metadata includes the same benefit counters.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
