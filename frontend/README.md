# AfyaSync staff web

React + TypeScript console connected to the real AfyaSync backend APIs.

## Features (wired to live endpoints)

- Login (`POST /api/v1/auth/login`)
- Multi-facility selection (`POST /api/v1/auth/select-facility`)
- Token refresh on 401 (`POST /api/v1/auth/refresh`)
- Logout session revoke (`POST /api/v1/auth/logout`)
- Facility dashboard report (`GET /api/v1/reports/facility`)
- Facility-scoped patient list/detail/create (`/api/v1/patients`)

Facility isolation and RBAC are enforced by the backend; the UI only uses facility-scoped tokens issued after login/selection.

## Run locally

```bash
# terminal 1 – API
cd backend && uvicorn app.main:app --reload --port 8000

# terminal 2 – web
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 — Vite proxies `/api` to the backend.
