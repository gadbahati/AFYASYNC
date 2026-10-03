# Phase 98 — Scoped-read surface hardening

**Developer:** BAHATI GAD WANGWE

## Gate criteria (release checklist)

| Check | Expected |
|-------|----------|
| Default scope | Omitting `?scope=` behaves as `facility` |
| Unauthorized scope | `403` with `SCOPE_NOT_AUTHORIZED` + `available_scopes` |
| Invalid scope string | `400 INVALID_OPERATING_SCOPE` |
| Empty facility set | Never — always falls back to token facility |
| Writes | Always JWT `facility_id` only (no scope expansion on create/update) |
| Audit | Scope denials and successful scope changes recorded |
| UI | Scope switcher reloads patients, encounters, claims, referrals, appointments, billing |

## Machine-readable inventory

Authenticated staff:

```http
GET /api/v1/context/scoped-surface
```

Returns `scoped_surface_manifest()` from `backend/app/context/scoped_surface.py`.

## Read endpoints (all accept `scope` where noted)

1. `GET /api/v1/context`
2. `GET /api/v1/context/scope-summary?scope=`
3. `GET /api/v1/context/operations-summary?scope=`
4. `POST /api/v1/context/scope?scope=`
5. `GET /api/v1/patients?scope=`
6. `GET /api/v1/patients/search?scope=`
7. `GET /api/v1/encounters?scope=`
8. `GET /api/v1/claims?scope=`
9. `GET /api/v1/referrals?scope=`
10. `GET /api/v1/referrals/transfers?scope=`
11. `GET /api/v1/appointments?scope=`
12. `GET /api/v1/billing/services?scope=`
13. `GET /api/v1/billing/invoices?scope=`

## Smoke commands (after login)

```bash
# Facility baseline
curl -H "Authorization: Bearer $TOKEN" "$API/api/v1/patients?limit=5&scope=facility"
curl -H "Authorization: Bearer $TOKEN" "$API/api/v1/claims?limit=5&scope=facility"

# Network (staff multi-facility or admin)
curl -H "Authorization: Bearer $TOKEN" "$API/api/v1/referrals?scope=network"

# Denial sample (non-admin)
curl -H "Authorization: Bearer $TOKEN" "$API/api/v1/patients?scope=national"
# expect 403 SCOPE_NOT_AUTHORIZED

# Inventory
curl -H "Authorization: Bearer $TOKEN" "$API/api/v1/context/scoped-surface"
```

## DHA / interoperability note

Scope is **authorization context**, not a substitute for HIE consent or national identity resolution. Broader scopes only expand **facility membership of result sets** for users already authorized by RBAC. Patient-level disclosure rules and consent gates remain separate modules.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
