# Phase 20 — Public trust layer (HARDENED)

**Developer:** BAHATI GAD WANGWE  
**Status:** Implemented + hardened — **roadmap complete (1–20)**

---

## Purpose

Give the public, government reviewers, and facilities a **transparent, non-PHI** view of what AfyaSync stands for — without exposing patients.

## Endpoints (no authentication)

| Method | Path | Content |
|--------|------|--------|
| `GET` | `/api/v1/public/trust` | Bundle: status + attribution + facility count |
| `GET` | `/api/v1/public/status` | Operational label (no hostnames) |
| `GET` | `/api/v1/public/attribution` | **BAHATI GAD WANGWE** copyright + prohibited uses |
| `GET` | `/api/v1/public/principles` | Trust, DPA-aligned, patient rights, government alignment |
| `GET` | `/api/v1/public/privacy` | Plain-language privacy summary |
| `GET` | `/api/v1/public/facilities` | Active facility directory (no emails, no patients) |

## Hardening

| Rule | Detail |
|------|--------|
| Zero PHI | No names, IDs, diagnoses, claims, or membership numbers |
| Minimal facility card | Code, name, type, county, phone only |
| No internal secrets | Environment reduced to production / non-production |
| Attribution locked | Developer name and anti-theft notice always present |
| Standalone first | Documented as SHA-integrated, not SHA-clone |

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
