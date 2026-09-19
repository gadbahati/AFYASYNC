# Phase 8 — SHA claims workbench UX

**Developer:** BAHATI GAD WANGWE

## What was delivered

Polished facility **Claims & rework** page (`/claims`):

| Feature | Detail |
|---------|--------|
| **Summary stats** | Total, in-flight, approved, rejected, claimed KES, paid KES |
| **Preflight** | Check invoice readiness before creating a claim |
| **Status filters** | Chip filters (ALL, DRAFT, READY, SUBMITTED, …) |
| **Workflow actions** | Validate → Submit → Payer response → Reconcile |
| **Sandbox reject** | Demo rejection without live SHA |
| **Rejection workbench** | Code, problem, fix guide, owner |

## API used

- `GET /api/v1/claims/invoices/{id}/preflight`
- `POST /api/v1/claims`
- `POST /api/v1/claims/{id}/validate`
- `POST /api/v1/claims/{id}/submit`
- `POST /api/v1/claims/{id}/response`
- `POST /api/v1/claims/{id}/reconcile`
- `POST /api/v1/claims/{id}/sandbox-reject`
- `GET /api/v1/claims/workbench/rejections`

## How staff use it

1. Enter invoice ID → **Run preflight**
2. If ready → **Create claim**
3. **Validate** then **Submit**
4. Record payer response or use sandbox reject for training
5. **Reconcile** when payment arrives
6. Fix rejected claims using the workbench guide

## Next

Phase 9: production migrations & deploy checklist.
