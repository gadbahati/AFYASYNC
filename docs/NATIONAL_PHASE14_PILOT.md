# National Phase 14 — Pilot Ops, Migration Readiness & Evidence Pack

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/pilot/checklist` | 10 pilot go-live gates |
| GET | `/api/v1/pilot/migration-readiness` | Migration domains + auto metrics |
| GET | `/api/v1/pilot/evidence-pack` | Combined cert + security + national + pilot |

## Go-live rule
`go_live_recommendation` is `HOLD` if security CRITICAL failures or national readiness NOT_READY; otherwise `READY_FOR_PILOT_REVIEW`.

## Honest limit
This is **evidence**, not a DHA certificate and not a signed facility board decision.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
