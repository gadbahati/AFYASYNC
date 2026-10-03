# Phase 99 — Permission-aware module actions

**Developer:** BAHATI GAD WANGWE

## Stack

```
RBAC permissions
  → allowed_workspaces (Phase 89)
  → allowed_paths / module_actions (Phase 99)
  → Workspace home link filter
  → API still enforces require_permission
```

## Backend

- `backend/app/context/module_actions.py` — path → permission prefix catalog
- `GET /api/v1/context` includes `module_actions.allowed_paths`
- Fixed workspace prefix matching (`startswith` on each prefix, not the whole tuple)

## Frontend

Workspace home only shows links whose path is in `allowed_paths`.

Unknown paths are denied for non-admins. Dashboard `/` is always allowed for authenticated staff.

## Policy

UI filtering is **not** security. Every mutating API continues to use `require_permission`.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
