# AfyaSync Disaster Recovery

AfyaSync production recovery is an infrastructure responsibility as well as an application responsibility. The application exposes readiness checks and uses PostgreSQL migrations; production recovery must additionally use managed PostgreSQL backups, tested restoration, encrypted storage, independent monitoring and documented recovery ownership.

## Recovery objectives

Set and approve service-specific RPO/RTO values before pilot. Do not treat arbitrary infrastructure defaults as approved recovery objectives.

## Required backup controls

- Automated PostgreSQL backups with encryption at rest.
- Point-in-time recovery where supported by the managed PostgreSQL service.
- Backup retention aligned with the approved data-retention policy.
- A recovery copy protected from the production account/failure domain.
- Quarterly restore exercises at minimum during pilot, then according to the approved operational schedule.
- Restore verification must include schema migration state, critical reference data and application `/ready` health.

## Recovery sequence

1. Declare the incident and assign an incident commander.
2. Preserve relevant audit/integration evidence.
3. Provision a clean PostgreSQL target in the approved recovery environment.
4. Restore the selected backup/PITR point.
5. Run the exact Alembic migration chain required by the released application.
6. Restore application secrets through the approved secret manager; never from Git.
7. Deploy the matching backend, worker and frontend versions.
8. Verify `/health` and `/ready`.
9. Verify authentication, facility isolation, a non-production smoke encounter, integration queue integrity and audit writes.
10. Reconcile payer/integration transactions before reopening external submission.
11. Monitor error rate and queue health closely after recovery.
12. Record the incident, recovery point, data-loss assessment, corrective actions and lessons learned.

## Offline and outage behaviour

The web client has an offline application-shell cache, but patient/clinical API data is deliberately excluded from service-worker caching. This prevents accidental PHI persistence in a browser cache. A true offline clinical transaction engine with conflict-safe synchronisation requires a separate approved workflow and security design and is not claimed by this shell cache.

## External dependency

Backup infrastructure, database point-in-time recovery, multi-zone/failover configuration, secret management and restore exercises cannot be proven by repository code alone. They must be configured and evidenced in the actual production environment.
