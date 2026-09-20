# Phase 9 — Production migrations & deploy checklist

**Developer:** BAHATI GAD WANGWE  
**Status:** Hardened — ready to execute on Render / Railway / Vercel + API

## Goal

Ship Phases 1–8 safely: schema via Alembic, secrets, CORS, SMS/email, smoke tests.

---

## Hardening (this pass)

| Control | Detail |
|---------|--------|
| Idempotent migration `0071` | Tables/indexes created only if missing (safe after non-prod `create_all`) |
| Unique constraints | Sensitive category / procedure codes, diagnosis consent, case numbers |
| Seed | `ON CONFLICT (code) DO NOTHING` for sensitive categories |
| `/ready` | In production, fails with 503 if Phase 9 tables are missing |
| `/ready` | Returns `alembic_revision` when available |
| Render | `healthCheckPath: /ready`; `preDeployCommand: alembic upgrade head` |
| Railway | `alembic upgrade head` before uvicorn; healthcheck `/ready` |
| Seed admin | Still blocked in production without `BOOTSTRAP_UNIVERSAL_ADMIN_ONCE` |
| Notifications | Default `SMS_PROVIDER`/`EMAIL_PROVIDER=console` until real providers set |

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
export DATABASE_URL="postgresql+psycopg://..."
alembic upgrade head
alembic current   # → 0071_beast_portal_consent_treat_abroad
```

> Production must **not** rely on `create_all`. Alembic is the schema authority.

---

## 2. Required environment variables

### API

| Variable | Production value |
|----------|------------------|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Managed Postgres (psycopg URL) |
| `JWT_SECRET` | ≥32 random characters |
| `CORS_ORIGINS` | Exact HTTPS frontend origin(s) |

### Notifications

| Variable | Example |
|----------|--------|
| `SMS_PROVIDER` | `http` (or `console` until wired) |
| `SMS_HTTP_URL` / `SMS_HTTP_API_KEY` | Gateway |
| `EMAIL_PROVIDER` | `smtp` |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Mail server |

### Frontend

| Variable | Value |
|----------|--------|
| `VITE_API_BASE_URL` | `https://your-api.example.com` (no trailing slash) |

---

## 3. Post-deploy smoke checklist

- [ ] `GET /health` → healthy  
- [ ] `GET /ready` → ready, `database: ok`, no `missing_tables`  
- [ ] `alembic current` → `0071_beast_portal_consent_treat_abroad`  
- [ ] Facility login  
- [ ] Patient register + login  
- [ ] Claims sandbox reject **blocked** in production  
- [ ] No `SEED_UNIVERSAL_ADMIN` without bootstrap flag  

---

## 4. Rollback

1. Stop traffic to bad release.  
2. App rollback if schema compatible.  
3. Do **not** hand-edit `alembic_version`.  
4. Tested downgrade only: `alembic downgrade 0070_allergy_permissions`.

---

## Next

**Phase 10:** pilot / go-live gate (UAT evidence, backups, SHA connector credentials, incident runbook).

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
