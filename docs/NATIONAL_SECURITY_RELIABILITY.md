# National-Grade Security and Reliability Baseline

## Controls implemented in the application

- Strong production JWT configuration validation
- HTTPS-only production CORS
- Facility-scoped authorisation with explicit national permissions
- Refresh-token rotation and revocation
- Authentication abuse limiting
- Request IDs and security response headers
- Generic production error responses
- Signed/idempotent external callbacks and retry-aware integration processing
- Alembic-only production schema management
- Audit events for sensitive national and authentication actions
- Aggregate-only national operational reporting

## Required infrastructure controls

The application cannot manufacture these external controls. Before live deployment, the operator must provide managed secrets, encrypted database/storage, network controls, centralised logs/alerts, tested backups, disaster-recovery procedures, vulnerability scanning, penetration testing, incident response and approved data-protection governance.

## Reliability objective

Integration failures must remain visible and recoverable. `PENDING`, `RETRYING` and `FAILED` transactions are operational states, not silent success. Operators should monitor the integration transaction queue and investigate persistent failures before reconciliation or claim deadlines are missed.
