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

## Deploy frontend on Vercel (simple)

The **web UI** fits Vercel well. The **FastAPI + PostgreSQL backend does not** — host the API elsewhere (Railway, Render, Fly.io, a VPS), then point the frontend at it.

1. Push this repo to GitHub (already on `main`).
2. In [Vercel](https://vercel.com): **Add New Project** → import `gadbahati/AFYASYNC`.
3. Set:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Environment variable:
   - `VITE_API_BASE_URL` = `https://your-api-host.example` (no trailing slash)
5. Deploy.

On the API host, set `CORS_ORIGINS` to your Vercel URL, e.g. `https://your-app.vercel.app`.

Without a live API URL, the Vercel site will load but login/patients will fail network calls — that is expected until the backend is deployed.
