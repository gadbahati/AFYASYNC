# Phase 110 — Claims client APIs + workbench restore

**Developer:** BAHATI GAD WANGWE

## Client methods added

| Method | Endpoint |
|--------|----------|
| `createClaim(invoiceId)` | `POST /api/v1/claims` |
| `validateClaim(id)` | `POST /api/v1/claims/{id}/validate` |
| `submitClaim(id)` | `POST /api/v1/claims/{id}/submit` |
| `recordClaimResponse(id, payload)` | `POST /api/v1/claims/{id}/response` |
| `reconcileClaim(id, amount)` | `POST /api/v1/claims/{id}/reconcile` |
| `listClaimRejections()` | `GET /api/v1/claims/workbench/rejections` |
| `claimsKesAtRisk(days)` | `GET /api/v1/claims/risk/kes-at-risk` |
| `sandboxRejectClaim(id)` | `POST /api/v1/claims/{id}/sandbox-reject` |
| `claimPreflight(invoiceId)` | (existing) |

## ClaimsPageBody

Full workbench (list, filters, validate/submit/response/reconcile, benefit preflight panel).

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
