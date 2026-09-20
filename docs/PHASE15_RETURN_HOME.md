# Phase 15 — Treat Abroad return-home package (HARDENED)

**Developer:** BAHATI GAD WANGWE  
**Status:** Implemented + hardened

---

## Problem

Patients returning from overseas treatment often lose structured continuity: foreign discharge notes never reach the Kenyan facility in a usable form, follow-up is informal, and SHA cases close without a clinical handoff.

## Solution

A **return-home package** is required before a case can move `TREATMENT_IN_PROGRESS → RETURNED`.

### Package contents (required)
- Discharge summary (≥30 chars)
- Procedures performed
- Medications on discharge
- Follow-up plan (≥20 chars)

### Optional
- Complications, foreign report refs, rehab flags, recommended follow-up date, local follow-up facility

---

## APIs

| Method | Path | Role |
|--------|------|------|
| `PUT` | `/api/v1/treat-abroad/cases/{id}/return-package` | Staff draft/save |
| `POST` | `/api/v1/treat-abroad/cases/{id}/return-package/issue` | Staff issue → case **RETURNED** |
| `GET` | `/api/v1/treat-abroad/cases/{id}/return-package` | Staff read |
| `GET` | `/api/v1/treat-abroad/portal/return-packages` | Patient (issued only) |

Migration: **`0076_return_packages`**

---

## Hardening

| Control | Detail |
|---------|--------|
| Gate | PATCH status=`RETURNED` without issued package → `RETURN_PACKAGE_REQUIRED` |
| Issue path | Preferred: `POST …/issue` (saves audit + patient notification) |
| Facility scope | Package tied to case facility |
| Immutable after issue | Draft updates rejected once `ISSUED` |
| Audit | `OVERSEAS_RETURN_PACKAGE_SAVED` / `_ISSUED` |

---

## Deploy

```bash
alembic upgrade head
```

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
