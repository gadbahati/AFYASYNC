# Phase 93 — UI scope wiring

**Developer:** BAHATI GAD WANGWE

## Goal

The active operating context from `/workspace` must drive list data on operational screens.

## Wired pages

| Page | API call |
|------|----------|
| Patients | `api.listPatients(50, 0, scope)` |
| Encounters | `api.listEncounters(100, 0, scope)` |
| Claims | `api.listClaims(50, scope)` |

## Client

`frontend/src/api/client.ts` now accepts `scope` on:

- `listPatients`
- `searchPatients`
- `listEncounters`
- `listClaims`

## Behaviour

1. User sets scope on `/workspace` (stored in session via `WorkspaceContext`).
2. Navigating to Patients / Encounters / Claims reloads with that scope.
3. Changing scope and returning to a list page re-fetches automatically.

Creates and write actions remain on the **token facility** only.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
