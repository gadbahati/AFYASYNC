# Phase 113 — Adjudication detail panel

**Developer:** BAHATI GAD WANGWE

## UI

On **Claims** workbench:

- **Adj. detail** — loads `GET /api/v1/adjudication/claims/{id}/lines`
- Panel shows overall decision, amounts, reason, timestamp
- Line table: submitted, allowed, decision, reason, service code
- Auto-opens after **Adjudicate** / **Re-adjudicate**

## API

Already from Phase 112:

- `GET /api/v1/adjudication/claims/{claim_id}/lines`
- Client: `api.getClaimAdjudicationLines(claimId)`

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
