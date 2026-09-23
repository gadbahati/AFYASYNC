# AfyaSync — System-Wide Harden

**Developer:** BAHATI GAD WANGWE

## Completed in this pass

| Area | Change |
|------|--------|
| `record_audit` | Best-effort; never crashes business APIs |
| Pilot evidence | Facility filter excludes only REJECTED/SUSPENDED/CLOSED (not ACTIVE-only) |
| National declaration | Correct service signatures + isolated gate failures |
| Risk register | Validated filters + safe seed |
| Routers in `main.py` | All phase modules registered (98 routers) |
| Migrations | Chain through `0096_residual_risks` |

## Deploy sequence

```bash
alembic upgrade head
# set ENVIRONMENT, JWT_SECRET, DATABASE_URL, CORS_ORIGINS
# GET /ready must succeed
# GET /api/v1/national-readiness/declaration (auth)
```

## No dummies

- Patient auth: self-registration only (no AFYA-TEST credentials)
- Secrets never returned from production readiness
- SHA live mode requires operator token

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
