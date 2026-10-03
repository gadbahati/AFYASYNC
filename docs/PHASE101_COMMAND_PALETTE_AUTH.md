# Phase 101 — Authorized global command palette

**Developer:** BAHATI GAD WANGWE

## Problem

Ctrl/Cmd+K previously filtered only by `allowed_workspaces`. Users could still search into module paths their role could not open, then hit Phase 100 route guards.

## Fix

`GlobalCommand` loads from `GET /api/v1/context`:

- `allowed_workspaces`
- `module_actions.allowed_paths`
- `module_actions.catalog_paths`
- admin flag

Each result must pass **workspace membership** and **`isPathAllowed`** (same helper as ModuleGuard).

## UX

- Empty search: up to 8 authorized shortcuts
- Query: up to 12 matches among authorized modules only
- Empty state: “No matching authorized module found.”

## Stack

```
RBAC → workspaces → module_actions → ModuleGuard → ⌘K palette
```

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
