# Phase 144 — Radiology route + worklist context params

**Developer:** BAHATI GAD WANGWE

## New route

| Path | Page |
|------|------|
| `/radiology` | `RadiologyPage` — imaging worklist + complete/forward |

Query params:

- `orderId` — focus that clinical imaging order
- `encounterId` — focus orders for that encounter

## Worklist deep-links

| Type | Link |
|------|------|
| LAB | `/laboratory?encounterId=&orderId=` |
| PHARMACY | `/pharmacy?encounterId=&orderId=` |
| IMAGING | `/radiology?encounterId=&orderId=` |

Lab already reads `patientId` / `encounterId`. Pharmacy reads `patientId`.

## App.tsx

Slim App now includes `/laboratory`, `/pharmacy`, `/radiology`, `/clinical-worklist`.
For the full historical tree still run `bash scripts/restore_app_tsx.sh` then re-add radiology if needed.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
