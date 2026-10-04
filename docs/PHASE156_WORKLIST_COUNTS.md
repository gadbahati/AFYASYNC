# Phase 156 — Worklist counts API

**Developer:** BAHATI GAD WANGWE

## Endpoint

`GET /api/v1/clinical/worklist/counts`

Requires facility context + `clinical.record.read`.

```json
{
  "facility_id": "…",
  "status": "ORDERED,IN_PROGRESS",
  "LAB": 3,
  "PHARMACY": 1,
  "IMAGING": 2,
  "total": 6,
  "developer": "BAHATI GAD WANGWE"
}
```

Single SQL `GROUP BY order_type` for open statuses.

## Dashboard

`ClinicalQueueStrip` uses this endpoint (one request instead of three).

**Note:** Register `/worklist/counts` before any `/{param}` routes if path order matters; currently static path is fine under `/worklist/counts`.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
