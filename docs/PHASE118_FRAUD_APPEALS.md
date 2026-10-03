# Phase 118 — Fraud scan + claim appeals

**Developer:** BAHATI GAD WANGWE

## Fraud scan

`POST /api/v1/claims/{claim_id}/fraud-scan`

Checks:
- Possible duplicate (same patient/payer/amount in 48h)
- High claim frequency (patient ≥5 other claims in 7 days)
- High-value claim (≥ KES 100,000)
- Missing lines
- Duplicate service codes on one claim

Returns `score` 0–100 and `band` CLEAR | LOW | MEDIUM | HIGH.

## Appeal

`POST /api/v1/claims/{claim_id}/appeal`

```json
{ "reason": "Clinical notes support medical necessity…", "evidence_ref": "optional" }
```

Only `REJECTED` → status `UNDER_REVIEW` + audit `CLAIM_APPEAL`.

## UI

Claims workbench: **Fraud scan** and **Appeal** on REJECTED rows.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
