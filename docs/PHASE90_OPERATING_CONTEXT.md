# Phase 90 — Operating Context Data Scope

**Developer:** BAHATI GAD WANGWE

## Direction

Phase 89 made workspaces and the ⌘K command palette **authorization-aware** (RBAC → allowed workspaces → UI).

Phase 90 makes the selected operating context change **which facilities’ data the API may aggregate**, not only what the UI shows.

```
User
  → Identity
  → RBAC roles + permissions
  → Authorized scopes (facility | network | county | national)
  → Resolved facility set
  → Scoped counts / future scoped queries
  → Workspace → Module → Action
```

## Scopes (real resolution)

| Scope | Who | Facility set |
|-------|-----|--------------|
| `facility` | All staff | Token facility only |
| `network` | All staff | All facilities where the user has ACTIVE staff membership |
| `county` | System Administrator | ACTIVE facilities in the same county as the token facility |
| `national` | System Administrator | All ACTIVE facilities |

Operational **writes** still require the token facility context (`FACILITY_CONTEXT_REQUIRED`). Scope expansion is for authorized **read/aggregate** views.

## APIs

- `GET /api/v1/context?scope=` — profile + allowed workspaces + resolved facility count
- `GET /api/v1/context/scope-summary?scope=` — facility list + patient / encounter / claim counts under that scope

## Frontend

`/workspace` shows live “Data under this scope” cards that re-fetch when the user changes Facility / Network / County / National.

## Client restore note

If `frontend/src/api/client.ts` was truncated during a tooling incident, restore with:

```bash
git show e43a34205e0da522a9372c69f12dfcb3eb36f780:frontend/src/api/client.ts > frontend/src/api/client.ts
```

Then ensure these two methods exist on `_apiCore`:

```ts
contextOverview: (scope?: string) => request("/api/v1/context" + (scope ? `?scope=${encodeURIComponent(scope)}` : "")),
contextScopeSummary: (scope: string = "facility") => request(`/api/v1/context/scope-summary?scope=${encodeURIComponent(scope)}`),
```

Or run `npm run assemble-client` in `frontend/` after chunks are present under `src/api/.client-chunks/`.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
