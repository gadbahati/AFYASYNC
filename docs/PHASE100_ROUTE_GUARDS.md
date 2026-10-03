# Phase 100 — Route guards (module access)

**Developer:** BAHATI GAD WANGWE

## Goal

Hiding workspace tiles (Phase 99) is not enough. Deep links such as `/claims` must be blocked when the role lacks the matching permission prefixes.

## Flow

```
ProtectedRoute (session + facility)
  → ModuleAccessProvider (loads GET /api/v1/context)
  → ModuleGuard (isPathAllowed)
  → Layout + pages
```

## Always allowed (facility staff shell)

- `/` dashboard
- `/workspace` workspace home

## Source of truth

`module_actions.allowed_paths` from the backend catalog in `module_actions.py`.

API routes still use `require_permission`. Guards only stop unauthorized **navigation**.

## Verify

1. Login as a restricted role.
2. Open `/workspace` — only permitted modules appear.
3. Paste a denied URL (e.g. `/claims`) — see **Module not authorized**.
4. Admin — all modules remain reachable.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
