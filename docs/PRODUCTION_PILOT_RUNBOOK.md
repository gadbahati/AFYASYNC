# Production / Pilot Runbook

This runbook is the final engineering gate before a real AfyaSync pilot. Passing CI does not constitute government approval, clinical accreditation, privacy approval or SHA production authorisation.

## Gate 1 — deployment

- Managed PostgreSQL is provisioned and encrypted.
- Production secrets are supplied by the deployment secret manager.
- `ENVIRONMENT=production` is set.
- CORS contains only trusted HTTPS origins.
- `alembic upgrade head` completes successfully.
- `/health` and `/ready` return expected status.
- API and integration worker run as separate processes.

## Gate 2 — data protection

- Least-privilege database and application credentials are used.
- Backups are enabled and restore-tested.
- Audit logs are retained according to the approved retention schedule.
- Patient exports and national reporting are access-controlled and minimised.
- Security testing and a DPIA are completed by the responsible organisation before pilot use.

## Gate 3 — payer integration

- SHA/payer credentials are issued through the authorised onboarding process.
- Sandbox eligibility, benefits, preauthorisation, claims, callbacks and payment flows are tested.
- Production endpoint allowlists and certificates are verified.
- Idempotency, retry and rejection/rework paths are tested.

## Gate 4 — pilot

- Pilot facilities and named administrators are approved.
- Staff roles and facility assignments are verified.
- Synthetic test records are removed or clearly separated before live use.
- Incident contacts, rollback criteria and support ownership are documented.
- A controlled smoke test covers registration → encounter → service → billing → claim → payer response → reconciliation.

## Stop conditions

Do not move to live patient use when a critical security test fails, database recovery is unverified, payer production access is unauthorised, or required governance/clinical approvals are incomplete.
