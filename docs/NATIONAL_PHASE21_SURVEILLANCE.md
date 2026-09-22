# National Phase 21 — Public Health Surveillance & Notifiable Events

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## APIs

| Path | Purpose |
|------|---------|
| `POST /api/v1/surveillance/events` | Report notifiable case |
| `GET /api/v1/surveillance/events` | Facility list |
| `POST .../status` | OPEN → SUBMITTED → ACKNOWLEDGED → CLOSED |
| `GET /api/v1/surveillance/aggregates` | De-identified counts |

**Migration:** `0091_surveillance` → `alembic upgrade head`

Conditions: MALARIA, CHOLERA, MEASLES, TB, COVID19, AFP, YELLOW_FEVER, MENINGITIS, OTHER

## Honest limit
Facility reporting + aggregates. National MoH IDSR feed connector is a later integration step.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
