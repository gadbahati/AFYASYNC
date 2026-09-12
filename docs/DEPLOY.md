# AfyaSync deploy guide (fix login from Vercel)

`REQUEST_FAILED` / `API_NOT_CONFIGURED` means the **frontend has no live API**.
Vercel only hosts the React app. The FastAPI + PostgreSQL backend must be hosted separately.

## 1. Deploy API (Render)

1. Open [Render](https://render.com) → New → Blueprint → connect `gadbahati/AFYASYNC`.
2. Use the repo `render.yaml` (creates Postgres + API).
3. After deploy, copy the API URL, e.g. `https://afyasync-api.onrender.com`.
4. Confirm `GET https://…/health` returns healthy.

With `ENVIRONMENT=development`, startup creates tables and seeds:

- **Username:** `afyasync.admin`
- **Password:** `Kenya@Health2026`

Set `CORS_ORIGINS` to your Vercel URL:

```text
https://afyasync-swart.vercel.app
```

## 2. Point Vercel at the API

In the Vercel project → Settings → Environment Variables:

| Name | Value |
|------|--------|
| `VITE_API_BASE_URL` | `https://your-api.onrender.com` (no trailing slash) |

Redeploy the frontend.

## 3. Sign in

1. Open `https://afyasync-swart.vercel.app/login`
2. `afyasync.admin` / `Kenya@Health2026`
3. Optional: Remember me

## Local alternative

```bash
docker compose up --build
cd frontend && npm install && npm run dev
```

API: http://127.0.0.1:8000 · Web: http://localhost:5173
