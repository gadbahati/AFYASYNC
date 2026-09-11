# AFYASYNC production readiness

## Probes

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness — process is up (safe for frequent checks) |
| `GET /ready` | Readiness — database reachable (`503` if not) |

## Deploy checklist

1. Set `ENVIRONMENT=production`
2. Set a strong `JWT_SECRET` (≥ 32 characters; never the development default)
3. Set `DATABASE_URL` to managed PostgreSQL
4. Run migrations: `alembic upgrade head` (includes `0026_post_hardening_permissions`)
5. Confirm `create_all` will not run (disabled when environment is production)
6. Run container as non-root image (`backend/Dockerfile`)
7. Point orchestrator readiness at `/ready` and liveness at `/health`

## CI guarantees

- Python compile of `app`, `migrations`, and `tests`
- Production JWT secret rejection guard
- Pytest suite including isolation and route registry smoke tests

## Permission seed

Migration `0026_post_hardening_permissions` installs codes used by hardened routers and maps them to default clinical roles. Re-run is safe (idempotent inserts).
