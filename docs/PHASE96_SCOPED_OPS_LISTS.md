# Phase 96 — Scoped operational lists (referrals, appointments, billing)

**Developer:** BAHATI GAD WANGWE

## Endpoints

| Endpoint | Query |
|----------|-------|
| `GET /api/v1/referrals?scope=` | facility / network / county / national |
| `GET /api/v1/referrals/transfers?scope=` | same |
| `GET /api/v1/appointments?scope=` | same |
| `GET /api/v1/billing/services?scope=` | same |
| `GET /api/v1/billing/invoices?scope=` | same |

Default remains `scope=facility`.

## Notes

- Referrals/transfers match when **source or destination** is in the resolved facility set (for `role=all`).
- Writes still use the **token facility only**.
- Unauthorized scopes return `403 SCOPE_NOT_AUTHORIZED` (Phase 95).

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
