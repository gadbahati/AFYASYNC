# AfyaSync Technical Production Gate

This gate defines what the repository can verify automatically. Passing it does **not** constitute statutory approval, clinical governance approval, procurement approval, accreditation, or authorization to process national health data.

## Repository-enforced controls

- Production rejects the development JWT secret and predictable secrets.
- Production requires the configured HS256 implementation, managed PostgreSQL using the psycopg driver, and explicit HTTPS browser origins.
- Production does not run SQLAlchemy `create_all`; schema changes are applied through Alembic.
- API responses carry request correlation IDs and baseline browser/security headers.
- Unhandled API errors return a generic response rather than internal exception details.
- Authentication uses short-lived access tokens and rotating, revocable refresh sessions.
- Facility-scoped permissions require an active staff assignment at the requested facility.
- National permissions are explicit and do not rely on the selected facility token.
- Integration callbacks require a configured environment-backed secret, a bounded timestamp, and constant-time HMAC comparison.
- Outbound integration transactions validate entity ownership against the facility before queuing.
- Integration processing has bounded retries and a processing lease.
- The integration worker is deployed separately from the API process.
- Backend compilation, dependency consistency, migration-head validation, and automated tests run in CI.
- Frontend production builds run in CI.
- Production Docker images run as a non-root application user and include a readiness health check.
- Browser authentication tokens are kept in session storage; remember-me persists only the username.

## External go-live gates

These cannot be honestly marked complete by source code alone:

- Data Protection Impact Assessment and ODPC/privacy review where required.
- Data-controller/processor roles, retention schedules, privacy notices, data-subject procedures, and lawful processing basis.
- Clinical governance owner, safety sign-off, incident management, and clinical validation.
- Facility onboarding, staff credentialing, licensing/accreditation, and operational acceptance.
- Security assessment/penetration testing and formal vulnerability management.
- Production database provisioning, encrypted backups, restore testing, disaster recovery, monitoring, and incident contacts.
- Payer/SHA/integration agreements, credentials, UAT, callback contracts, and reconciliation acceptance.
- National interoperability/data-exchange approval and any required government procurement or authorization.

A technical CI pass means the repository is internally consistent and its automated controls pass. It must never be presented as evidence of government adoption or regulatory approval.
