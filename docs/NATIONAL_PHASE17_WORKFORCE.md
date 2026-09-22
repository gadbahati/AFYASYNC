# National Phase 17 — Workforce, Licensing & Credential Checks

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## APIs

| Path | Purpose |
|------|---------|
| `POST /api/v1/workforce/credentials` | Register/update licence |
| `GET /api/v1/workforce/staff/{id}/check` | CLEAR / WARN / EXPIRED / BLOCK / MISSING |
| `GET /api/v1/workforce/compliance` | Facility missing/expiring licences |

**Migration:** `0088_workforce_credentials` → `alembic upgrade head`

Councils: KMPDC, NCK, PPB, COC, OTHER.

## Honest limit
Local credential store — live council API verification comes when you obtain official registry connectors.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
