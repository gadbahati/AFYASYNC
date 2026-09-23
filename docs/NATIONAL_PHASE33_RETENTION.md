# National Phase 33 — Data Retention, Archival & Right-to-Erasure Ops

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## APIs

| Path | Purpose |
|------|---------|
| `GET /api/v1/retention/policies` | Retention catalogue by data class |
| `POST /api/v1/retention/requests` | Open ERASURE / RESTRICTION / ACCESS_EXPORT |
| `GET /api/v1/retention/requests` | List facility requests |
| `POST .../decide` | Review; optional pseudonymisation |

**Migration:** `0092_erasure_requests` → `alembic upgrade head`

## Honest limit
Fulfilment **pseudonymises** identifiers; it does not destroy claims/audit history required by law.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
