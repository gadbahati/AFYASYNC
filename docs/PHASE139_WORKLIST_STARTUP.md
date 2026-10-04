# Phase 139 — Clinical worklist + startup/ready checks

**Developer:** BAHATI GAD WANGWE

## Worklist API

| Method | Path |
|--------|------|
| GET | `/api/v1/clinical/worklist?order_type=IMAGING\|LAB\|PHARMACY` |
| GET | `/api/v1/clinical/worklist/imaging` |

Default status filter: `ORDERED` + `IN_PROGRESS`.

## Startup / ready

- Startup runs `run_clinical_startup_checks()` (logs empty lab/pharmacy services).
- `/ready` includes `clinical_departments` status when checks run.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
