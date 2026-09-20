# Phase 12 — Consent-aware continuity card / QR wallet (HARDENED)

**Developer:** BAHATI GAD WANGWE  
**Status:** Implemented + hardened

---

## What it is

A patient-held **continuity token** (printable / QR) that any facility can verify.  
The snapshot is **consent-aware**: sensitive diagnoses appear **only** when the patient signed **CROSS_FACILITY** disclosure.

---

## APIs

| Route | Who | Purpose |
|-------|-----|--------|
| `POST /api/v1/portal/continuity-card/issue` | Patient | Issue card (token shown once) |
| `GET /api/v1/portal/continuity-card` | Patient | List active/revoked cards |
| `POST /api/v1/portal/continuity-card/{id}/revoke` | Patient | Revoke |
| `POST /api/v1/continuity/verify` | Public | Verify token → snapshot |
| `GET /api/v1/continuity/verify/{token}` | Public | Same |
| `POST /api/v1/facility/continuity/scan` | Facility staff | Audit-tagged scan |

Migration: `0073_continuity_cards`  
Readiness: `continuity_cards` in production table gate.

---

## Security / hardening

| Control | Detail |
|---------|--------|
| Token storage | **SHA-256 hash only** — raw token never stored |
| Prefix | First 8 chars for UI recognition only |
| Expiry | 365 days |
| Max active | 3 per patient (oldest rotated) |
| Consent filter | Sensitive DX without CROSS_FACILITY **omitted** |
| Audit | ISSUE / REVOKE / VERIFY actions |
| Facility scope | Scan requires authenticated staff + `patients:read` |

---

## UI

- Patient: `/portal/continuity-card` — issue, QR, revoke  
- Public: `/continuity` or `/continuity/:token`  
- Facility: **Continuity card scan** in sidebar  

---

## Deploy

```bash
alembic upgrade head   # applies 0073
```

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
