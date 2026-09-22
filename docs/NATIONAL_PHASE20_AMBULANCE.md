# National Phase 20 — Ambulance & Emergency Transport Depth

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## APIs

| Path | Who | Purpose |
|------|-----|---------|
| `POST /api/v1/ambulance/requests` | Patient | Request transport |
| `GET /api/v1/ambulance/my-requests` | Patient | Track my requests |
| `POST /api/v1/ambulance/facility/requests` | Facility | Log dispatch request |
| `GET /api/v1/ambulance/facility/board` | Facility | Priority board |
| `POST .../status` | Facility | REQUESTED→DISPATCHED→EN_ROUTE→ARRIVED→COMPLETED |

**Migration:** `0090_ambulance` → `alembic upgrade head`

## Honest limit
Operational workflow only — no live GPS fleet tracking until external CAD/GPS feed is connected.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
