# Phase 17 — Multi-payer truth + out-of-pocket estimate (HARDENED)

**Developer:** BAHATI GAD WANGWE  
**Status:** Implemented + hardened

---

## Problem

Patients and cashiers often guess whether SHA, private insurance, or cash will apply. Single-payer adjudication alone does not show the **truth table** across all active covers or a clear **patient OOP**.

## Solution

`POST /api/v1/coverage/oop-estimate` scores **every active coverage** for a basket of services and returns:

| Field | Meaning |
|-------|--------|
| `cash_oop` | Full patient pay (always available) |
| `options[]` | Per-payer eligibility, covered total, patient OOP, line breakdown |
| `recommended_*` | Best claimable option (SHA preferred on ties) |
| `stacked` | Optional primary + secondary residual model |

Patient self-service: `POST /api/v1/coverage/portal/oop-estimate` (own `person_id` only).

---

## Hardening

| Control | Detail |
|---------|--------|
| Facility path | Patient must be enrolled at facility |
| Claimable | Only `VERIFIED` + in-date + active plan |
| Rules | Plan-specific benefit rules preferred over payer-wide |
| Caps | Amounts and line counts bounded |
| Audit | `OOP_ESTIMATE` with totals (no clinical free-text dump) |
| Honesty | Stacked COB marked as estimate pending contract rules |

Standalone-first: **cash is always a valid path**.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
