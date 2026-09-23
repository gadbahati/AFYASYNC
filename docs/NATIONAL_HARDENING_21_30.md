# Hardening Gate — National Phases 21–30

**Developer:** BAHATI GAD WANGWE  
**Status:** HARDENED

## Router registration (main.py)

All present and included:

| Module | Prefix |
|--------|--------|
| surveillance | `/api/v1/surveillance` |
| quality_scorecard | `/api/v1/quality` |
| fraud_integrity | `/api/v1/fraud-integrity` |
| security_ops | `/api/v1/security-ops` |
| reliability | `/api/v1/reliability` |
| onboarding | `/api/v1/onboarding` |
| training | `/api/v1/training` |
| rollout | `/api/v1/rollout` |
| warehouse | `/api/v1/warehouse` |
| certification | `/api/v1/certification` (+ submission-kit) |

## Schema alignment

| Area | Check |
|------|--------|
| InventoryItem | `current_quantity` / `minimum_quantity` |
| EmergencyVisit | `status`, `facility_id` |
| Referral | `source_facility_id`, `status` |
| Claim | join via `Encounter.facility_id` |
| Encounter | `started_at` for window filters |
| NotifiableEvent | migration `0091_surveillance` |
| Staff | no `user_id` — onboarding uses professional_number |

## Fixes applied in this gate

1. Quality national scorecard: silent `except` → logged + `errors[]`
2. Warehouse: prefer `Encounter.started_at`; empty CSV still emits header
3. Rollout: removed facility UUID lists from county payload
4. Pilot evidence: linked warehouse + submission-kit endpoints

## Smoke tests (after `alembic upgrade head`)

```
GET /health
GET /ready
GET /api/v1/surveillance/aggregates
GET /api/v1/quality/facility-scorecard
GET /api/v1/fraud-integrity/facility-scan
GET /api/v1/security-ops/checklist
GET /api/v1/reliability/readiness-matrix
GET /api/v1/onboarding/facility-kit
GET /api/v1/training/catalog
GET /api/v1/rollout/county-dashboard
GET /api/v1/warehouse/facts
GET /api/v1/certification/submission-kit
```

## Still operator-owned

- Live SHA/DHA credentials
- External pen-test
- DHA portal filing

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
