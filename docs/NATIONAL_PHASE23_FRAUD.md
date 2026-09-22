# National Phase 23 — Fraud Detection Depth & Claims Integrity

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## APIs

| Path | Purpose |
|------|---------|
| `GET /api/v1/fraud-integrity/facility-scan` | Signals + integrity score |
| `GET /api/v1/fraud-integrity/national-overview` | Status volume + top facilities |

Signals: MULTI_CLAIM_SAME_DAY, AMOUNT_OUTLIER, NON_POSITIVE_AMOUNT

## Honest limit
Investigative flags only — require human review; not automatic fraud conviction.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
