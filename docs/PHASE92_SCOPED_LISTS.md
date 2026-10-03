# Phase 92 — Scoped List Endpoints

**Developer:** BAHATI GAD WANGWE

## Goal

Operating scope must filter high-traffic **list** APIs, not only workspace summaries.

## Endpoints updated

| Endpoint | Query | Behaviour |
|----------|-------|-----------|
| `GET /api/v1/patients?scope=` | `facility` (default), `network`, `county`, `national` | Lists enrollments across resolved facilities |
| `GET /api/v1/patients/search?scope=` | same | Search within resolved facilities |
| `GET /api/v1/encounters?scope=` | same | Lists encounters across resolved facilities |
| `GET /api/v1/claims?scope=` | same | Lists claims whose invoices belong to resolved facilities |

## Authorization

`resolve_facility_ids()` (Phase 90) remains the single source of truth:

- Ordinary staff → `facility` or `network` only
- System administrator → also `county` / `national`
- Unauthorized scope → `403 SCOPE_NOT_AUTHORIZED`

**Writes** (create patient, create encounter, create claim) still use the **token facility only**.

## Default

Omitting `scope` keeps prior behaviour (`facility` = token facility only).

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
