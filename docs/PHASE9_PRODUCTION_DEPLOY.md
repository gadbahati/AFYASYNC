# Phase 9 — Production migrations & deploy checklist

**Developer:** BAHATI GAD WANGWE  
**Status:** Ready to execute on your hosting (Render / Railway / Vercel + API)

## Goal

Ship Phases 1–8 safely: schema via Alembic, secrets, CORS, SMS/email, smoke tests.

---

## 1. Database migration (required)

New revision: **`0071_beast_portal_consent_treat_abroad`**

Creates:

| Table | Purpose |
|-------|--------|
| `patient_password_reset_tokens` | Patient portal password reset codes |
| `sensitive_categories` | HIV, mental health, STI, GBV, substance |
| `sensitive_disease_consents` | Digital disclosure consent |
| `approved_overseas_procedures` | SHA Treat Abroad catalogue |
| `overseas_treatment_cases` | Treat Abroad cases |
| `appointment_requests` | Patient → facility booking |
| `facility_messages` | Two-way patient/facility chat |

### Commands

```bash
cd backend
# Use production DATABASE_URL
export DATABASE_URL="postgresql+psycopg://..."
alembic upgrade head
alembic current   # should show 0071_beast_portal_consent_treat_abroad
```

On **Render**, `preDeployCommand: alembic upgrade head` already runs this.

> Production must **not** rely on `create_all`. Alembic is the schema authority.

---

## 2. Required environment variables

### API (backend)

| Variable | Production value |
|----------|------------------|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Managed Postgres (psycopg URL) |
| `JWT_SECRET` | ≥32 random characters |
| `CORS_ORIGINS` | Exact HTTPS frontend origin(s), comma-separated |
| `ACCESS_TOKEN_MINUTES` | e.g. `15` |
| `REFRESH_TOKEN_DAYS` | e.g. `30` |

### Notifications (Phase 7)

| Variable | Example |
|----------|--------|
| `SMS_PROVIDER` | `http` (or `console` only for non-prod) |
| `SMS_HTTP_URL` | Your SMS gateway endpoint |
| `SMS_HTTP_API_KEY` | Gateway key |
| `SMS_SENDER_ID` | `AfyaSync` |
| `EMAIL_PROVIDER` | `smtp` |
| `SMTP_HOST` | `smtp.example.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` / `SMTP_PASSWORD` | Credentials |
| `SMTP_FROM` | `noreply@yourdomain` |
| `SMTP_USE_TLS` | `true` |

### Frontend

| Variable | Value |
|----------|--------|
| `VITE_API_BASE_URL` | `https://your-api.example.com` (no trailing slash) |

Rebuild the frontend after changing `VITE_*`.

---

## 3. Deploy topology

```text
Browser (HTTPS)
  → Frontend (Vercel / Render static)
  → API (Render / Railway Docker)
       → PostgreSQL (private)
       → Worker (integrations)
```

- DB must not be public.
- API health: `/health` (liveness), `/ready` (readiness + DB).
- Worker runs separately: `python -m app.integrations.worker_runner`

---

## 4. Post-deploy smoke checklist

### System

- [ ] `GET /health` → healthy  
- [ ] `GET /ready` → ready, database ok  
- [ ] `alembic current` → `0071_beast_portal_consent_treat_abroad`

### Staff

- [ ] Facility login works  
- [ ] Facility selection restricted  
- [ ] Claims page loads; sandbox reject **fails** in production  
- [ ] Treat Abroad page lists procedures (after seed if empty)

### Patient portal

- [ ] Create patient account (Afya ID + name + password)  
- [ ] Sign out and sign in again  
- [ ] Portal home loads  
- [ ] Book appointment request  
- [ ] Send facility message  
- [ ] Password reset request does not leak codes in HTTP body

### Security

- [ ] `ENVIRONMENT=production`  
- [ ] Default JWT secret rejected  
- [ ] CORS only HTTPS frontend  
- [ ] No secrets in Git or frontend bundle  
- [ ] Cross-facility isolation spot-check

---

## 5. Rollback notes

1. Stop traffic to bad release.  
2. Prefer app rollback if schema is backward-compatible.  
3. Do **not** force `alembic_version` by hand.  
4. Schema downgrade only if tested: `alembic downgrade 0070_allergy_permissions`.

---

## 6. What Phase 9 does *not* claim

- Government approval or SHA certification  
- Live SHA eligibility API (needs official credentials)  
- Production SMS/email until you set real providers  

Those belong to **Phase 10** (pilot / go-live gate).

---

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
