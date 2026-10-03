# Phase 107 — Preauthorization work queue UI

**Developer:** BAHATI GAD WANGWE

## What landed

Facility **Preauthorization exchange** page now includes:

- Request form (person, coverage, payer, service, amount)
- Current authorization card with Authorize / Conditional / Reject
- **Work queue** table filtered by status (default PENDING)
- One-click Authorize / Reject from the queue

## Client APIs

```ts
api.financingPreauthCreate(payload)
api.financingPreauthDecide(id, payload)
api.financingPreauthList({ status?, person_id?, limit? })
```

Maps to:

- `POST /api/v1/financing-preauthorizations`
- `POST /api/v1/financing-preauthorizations/{id}/decision`
- `GET /api/v1/financing-preauthorizations`

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
