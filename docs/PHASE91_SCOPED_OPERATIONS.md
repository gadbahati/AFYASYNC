# Phase 91 — Scoped Operational Aggregates

**Developer:** BAHATI GAD WANGWE

## Goal

Operating context must change **backend data**, not only workspace navigation.

## API

```
GET /api/v1/context/operations-summary?scope=facility|network|county|national
    &start_date=YYYY-MM-DD
    &end_date=YYYY-MM-DD
```

Requires:
- Authenticated staff token with facility context
- Permission `reports.read`
- Scope still constrained by Phase 90 authorization (staff → facility/network; admin → county/national)

Returns:
- Resolved facility list
- Patients, encounters, charges, invoices, payments, claims (amount / approved / paid)

## Relationship to facility report

| Endpoint | Purpose |
|----------|---------|
| `/api/v1/reports/facility` | Single-facility operational detail |
| `/api/v1/context/operations-summary` | Multi-facility aggregate under authorized scope |

Writes remain facility-scoped via the access token.

## UI

`/workspace` loads both scope-summary and operations-summary when the user changes operating context.

## Client note

`frontend/src/api/client.ts` currently carries core auth + context + common methods plus `citizenApiMethods`. Restore the full historic client from commit `e43a3420` if a page still calls a missing method, then re-add:

- `contextOverview`
- `contextScopeSummary`
- `contextOperationsSummary`

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
