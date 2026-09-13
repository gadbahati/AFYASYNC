# AfyaSync Production Deployment Runbook

## Scope

This runbook covers a production deployment of the AfyaSync API, PostgreSQL database, background integration worker, and React web application.

AfyaSync must not receive real patient data until the organisation has completed its required legal, privacy, security, clinical governance, licensing, accreditation, payer, and interoperability reviews.

## Required topology

```text
Browser
  |
  | HTTPS
  v
TLS reverse proxy / load balancer
  |---------------------> React static application
  |
  +---------------------> FastAPI API -----> PostgreSQL
                              |
                              +-------------> Integration worker
```

The database must not be publicly exposed. The API and worker should run in private network segments where the deployment platform supports this.

## Production environment

Set these values through the deployment platform's secret/configuration manager:

- `ENVIRONMENT=production`
- `DATABASE_URL` for the managed PostgreSQL instance
- `JWT_SECRET` with a cryptographically random value of at least 32 characters
- `CORS_ORIGINS` containing only the exact trusted web origins
- DB pool settings appropriate for the managed database capacity
- provider credentials only through environment variables referenced by integration configuration

Do not commit `.env` files, JWT secrets, database passwords, API tokens, callback secrets, or private keys.

## Database migration

Before releasing application code that depends on a schema change:

1. Back up the production database.
2. Deploy the new application image/code.
3. Run `alembic upgrade head` using the production `DATABASE_URL`.
4. Confirm the migration command completed successfully.
5. Check `/ready`.
6. Start or restart API and worker processes.

Production application startup must not use SQLAlchemy `create_all`; Alembic is the schema authority.

For a failed migration, stop the rollout and restore/fix the migration before serving traffic. Do not manually edit the Alembic version table to bypass a failed migration.

## API health checks

- `/health` checks application availability.
- `/ready` checks database readiness and returns HTTP 503 when the database is unavailable.

Configure the load balancer/container platform to use `/ready` for readiness and `/health` for a lightweight liveness check.

## Worker

The integration worker is responsible for outbound payer/integration delivery and retries. Run it as a separate process from the API so API traffic remains available when integration delivery is delayed.

Workers must use the same production database and integration environment variables as the API. Only one deployment process should claim a transaction at a time; the database transaction/lease logic is the concurrency boundary.

Monitor:

- `PENDING` transactions
- `RETRYING` transactions
- `FAILED` transactions
- processing age
- attempt counts
- payer callback failures

## Frontend

Build the React application with the production API URL:

`VITE_API_BASE_URL=https://api.your-domain.example`

Serve the resulting static files over HTTPS. Configure the web server/load balancer to return `index.html` for client-side application routes.

The browser must never contain database credentials, payer secrets, JWT signing secrets, or callback secrets.

## Backups and restore

Use the managed PostgreSQL provider's automated backups plus a tested recovery process. At minimum:

- daily automated backups
- retention appropriate to the organisation's recovery requirements
- encrypted backups
- restricted backup access
- periodic restore tests in an isolated environment
- documented recovery point and recovery time objectives

A backup that has never been restored is not considered verified.

## Pilot onboarding

Before a pilot facility is allowed to process real data:

1. Register and verify the facility.
2. Create named staff accounts; never share accounts.
3. Assign least-privilege facility roles.
4. Confirm facility isolation with a cross-facility access test.
5. Configure only the payer integrations required by the pilot.
6. Store integration credentials outside the database.
7. Verify audit events for clinical, financial, claims, and administrative actions.
8. Test coverage verification and preauthorization.
9. Test claim submission, payer response, rejection/rework, and reconciliation.
10. Test standalone cash/private-payer care without a payer integration dependency.
11. Verify notifications do not expose unnecessary patient information.
12. Complete clinical, privacy, security, and operational sign-off.

## Rollback

Application rollback and database rollback are separate decisions. Prefer backward-compatible migrations. Do not automatically downgrade production schema after an application rollback unless the downgrade has been explicitly tested and approved.

If the application is unhealthy after release:

1. Stop routing new traffic to the unhealthy release.
2. Preserve logs and request IDs.
3. Inspect migration and application errors.
4. Roll back application code when the schema remains compatible.
5. If schema recovery is required, use the approved database recovery procedure.
6. Re-run `/ready` and critical smoke tests before restoring traffic.

## Minimum production smoke test

After deployment verify:

- login succeeds for a test account
- facility selection is restricted to authorised facilities
- patient registration/search works
- encounter creation works
- clinical record writes work
- billing and payment work
- claim validation/submission paths are available where configured
- integration callbacks are authenticated
- national functions remain permission restricted
- `/health` is healthy
- `/ready` is ready
- audit records are created for tested privileged actions

Do not use fake patient, claim, payment, or payer responses to represent production readiness.
