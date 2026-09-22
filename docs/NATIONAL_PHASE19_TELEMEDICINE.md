# National Phase 19 — Telemedicine & Remote Care Coordination

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## APIs

| Path | Who | Purpose |
|------|-----|---------|
| `POST /api/v1/telemedicine/requests` | Patient | Request remote consult |
| `GET /api/v1/telemedicine/my-requests` | Patient | List my requests |
| `POST .../cancel` | Patient | Cancel open request |
| `GET /api/v1/telemedicine/facility/inbox` | Facility | Open requests |
| `POST .../respond` | Facility | Accept/deny + schedule |
| `POST .../complete` | Facility | Clinical summary |

**Migration:** `0089_telemedicine` → `alembic upgrade head`

## Honest limit
Coordination workflow only — no embedded video SDK; use external meeting link in facility_message when accepting.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
