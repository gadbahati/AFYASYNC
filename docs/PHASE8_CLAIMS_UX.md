# Phase 8 — SHA claims workbench UX

**Developer:** BAHATI GAD WANGWE

## What was delivered

Polished facility **Claims & rework** page (`/claims`):

| Feature | Detail |
|---------|--------|
| **Summary stats** | Total, in-flight, accepted, rejected, claimed KES, paid KES |
| **Preflight** | Check invoice readiness before creating a claim |
| **Status filters** | DRAFT, READY, SUBMITTED, UNDER_REVIEW, ACCEPTED, … |
| **Workflow actions** | Validate → Submit → Payer response → Reconcile |
| **Sandbox reject** | Demo only — **blocked in production** |
| **Rejection workbench** | Code, problem, fix guide, owner |

## Hardening

| Control | Detail |
|---------|--------|
| Status machine | UI actions gated by claim status |
| Canonical statuses | `APPROVED` → `ACCEPTED`, `PARTIALLY_APPROVED` → `PARTIALLY_PAID` |
| Invoice ID | UUID format validated client-side |
| Response fields | Max lengths (code 80, message 500, reference 150) |
| Amounts | Non-negative; approved amount required except REJECTED |
| Sandbox reject | Disabled when `ENVIRONMENT=production` |
| Schema bounds | Approved/received amount max 100,000,000 KES |
| Facility scope | All claim operations still facility-isolated + permissioned |

## Canonical claim statuses

`DRAFT` → `READY` → `SUBMITTED` → `UNDER_REVIEW` → `ACCEPTED` / `PARTIALLY_PAID` / `REJECTED` → `PAID`

## API used

- `GET /api/v1/claims/invoices/{id}/preflight`
- `POST /api/v1/claims`
- `POST /api/v1/claims/{id}/validate`
- `POST /api/v1/claims/{id}/submit`
- `POST /api/v1/claims/{id}/response`
- `POST /api/v1/claims/{id}/reconcile`
- `POST /api/v1/claims/{id}/sandbox-reject` (non-production only)
- `GET /api/v1/claims/workbench/rejections`

## Next

**Phase 9:** production migrations & deploy checklist.
