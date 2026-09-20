# Phase 11 — SHA rejection prevention engine (HARDENED)

**Developer:** BAHATI GAD WANGWE  
**Status:** Implemented + hardened

---

## Goal

Stop bad claims **before** they hit the payer. Give facilities a money-focused view of **KES at risk**.

---

## What shipped

### 1. Risk score on every preflight

`GET /api/v1/claims/invoices/{invoice_id}/preflight` now returns:

| Field | Meaning |
|-------|--------|
| `risk_score` | 0–100 rejection likelihood |
| `risk_band` | LOW / MEDIUM / HIGH / CRITICAL |
| `block_submit` | True if hard errors or score ≥ 70 |
| `risk_factors[]` | code, severity, points, message, **owner** |

Scoring uses real preflight errors/warnings (coverage, totals, cash encounter, payer status, etc.) — **not** random dummy scores.

### 2. Facility KES at risk

`GET /api/v1/claims/risk/kes-at-risk?days=7`

- Scoped to **caller’s facility only**
- Sums rejected + in-flight claim amounts in the window
- Also reports draft/ready value for pipeline visibility

### 3. Audit

Preflight audit metadata includes `risk_score`, `risk_band`, `block_submit`.

---

## Hardening

| Control | Detail |
|---------|--------|
| Facility isolation | Invoice + risk aggregates filtered by `facility_id` |
| Permission | `CLAIMS_VALIDATE` required |
| No cross-facility probe | Unknown invoice → same not-found path |
| Caps | Score max 100; days query 1–90 |
| Production | Sandbox reject remains blocked (Phase 8/9) |
| No dummy scores | Empty factors when clean invoice |

---

## Stakeholder benefits

| Stakeholder | Benefit |
|-------------|--------|
| **Hospital** | See KES stuck/rejected; fix before submit |
| **Government** | Cleaner inbound claims |
| **Individual** | Fewer “your bill is stuck on claim” delays |

---

## How to use

1. Billing produces invoice UUID.  
2. Claims page → **Run preflight**.  
3. Read risk band + factors (owner column tells who fixes).  
4. Only create/submit when ready and not blocked.  
5. Watch **KES at risk** weekly for facility management.

---

## Next

**Phase 12:** Consent-aware continuity card / QR wallet.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
