# Phase 94 — Global operating scope switcher

**Developer:** BAHATI GAD WANGWE

## Goal

Staff should change operating scope without returning to `/workspace` every time.

## UI

| Location | Behaviour |
|----------|-----------|
| **Sidebar** | “OPERATING SCOPE” select (facility / network / county / national) |
| **Top bar** | Teal badge `SCOPE: FACILITY` (updates live) |

Unauthorized scopes are disabled using `available_scopes` from `GET /api/v1/context`.

If the stored scope is no longer authorized, the UI falls back to the first allowed scope.

## Persistence

Scope remains in `sessionStorage` (`afyasync.context-scope`) via `WorkspaceContext`.

## Effect

Changing the sidebar select updates context immediately. Patients, Encounters, Claims, and workspace metrics re-fetch with the new scope (Phase 93).

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
