# Phase 95 — Operating scope audit & denial UX

**Developer:** BAHATI GAD WANGWE

## Goal

Scope changes must be auditable. Unauthorized scope must never look like an empty dataset.

## Backend

| Action | When |
|--------|------|
| `SET_OPERATING_SCOPE` | Successful `POST /api/v1/context/scope` |
| `SCOPE_CHANGE_DENIED` | Explicit change rejected by RBAC |
| `SCOPE_NOT_AUTHORIZED` | List/summary path requests a forbidden scope |

`403` body:

```json
{
  "detail": {
    "code": "SCOPE_NOT_AUTHORIZED",
    "message": "Your role cannot use 'national' scope. Allowed: facility, network.",
    "available_scopes": ["facility", "network"]
  }
}
```

## Frontend

- Sidebar scope select calls `api.setOperatingScope` **before** updating local state.
- On denial: clear error under the select; scope does not change.
- Restricted options remain disabled from `available_scopes`.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
