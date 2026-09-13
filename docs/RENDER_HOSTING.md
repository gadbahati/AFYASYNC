# Hosting AfyaSync on Render (interim)

Use Render while you evaluate a longer-term host. Keep the UI professional; point it at a live API.

## Frontend (static / web service)

- Root directory: `frontend`
- Build: `npm install && npm run build`
- Publish: `dist`
- Env:
  - `VITE_API_BASE_URL` = your API origin, e.g. `https://afyasync-api.onrender.com` (no trailing slash)

## Backend (web service)

- Root directory: `backend` (or monorepo root with start command into backend)
- Start: e.g. `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env: `DATABASE_URL`, `ENVIRONMENT`, JWT secrets, `CORS` origins including the frontend URL

## CORS

Allow the Render frontend origin in backend CORS settings or the browser will block API calls.

## Look & feel

The UI uses a clinical design system (IBM Plex, deep green, clean cards). Avoid enabling demo/bypass mode on a shared public URL if you are showing stakeholders real product intent.
