# Phase 16 — County / national care-gap intelligence (HARDENED)

**Developer:** BAHATI GAD WANGWE  
**Status:** Implemented + hardened

---

## Purpose

Give **MOH / county** operators a single aggregate view of where the system is under stress — without exposing patient identities.

## Gap score (0–100)

Composite heuristic from:

| Signal | Examples |
|--------|----------|
| Encounter load | Open encounters per facility |
| Referral outflow | Outbound referrals in window |
| Treat Abroad | Open overseas cases |
| Access | Pending patient appointment requests |
| Claims quality | Rejection rate |
| Supply | Low-stock pharmacy items |
| Acute care | Emergency load, bed occupancy |

---

## APIs (national permission required)

| Method | Path |
|--------|------|
| `GET` | `/api/v1/national/care-gaps/overview` |
| `GET` | `/api/v1/national/care-gaps/counties` |
| `GET` | `/api/v1/national/care-gaps/counties/{county}` |

Query: `window_days` (7–90, default 30), `top_n` (1–47).

Permission: `reports.national.read` via `require_national_permission`.

---

## Hardening

| Control | Detail |
|---------|--------|
| Aggregate only | No patient IDs, names, or clinical free-text |
| Auth | National reports permission only |
| Audit | `VIEW_CARE_GAP` on every query |
| Bounds | Window and top_n clamped |
| Honest notes | Scores are operational heuristics, not diagnoses |

No new migration (reads existing operational tables).

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
