# Phase 149 — Referrals route + imaging on summary

**Developer:** BAHATI GAD WANGWE

## Frontend

- `/referrals` → `ReferralsPage` (real page, not messages alias)

## Backend summary

`GET /api/v1/encounters/{id}/summary` includes:

```json
"imaging_reports": [
  {
    "order_id": "…",
    "code": "…",
    "description": "…",
    "status": "COMPLETED",
    "modality": "CT",
    "impression": "…",
    "notes": "…"
  }
]
```

Parsed from fulfilled IMAGING order notes (`Modality:` / `Impression:` lines from Phase 147).

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
