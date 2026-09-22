# National Phase 7 — Imaging / Radiology Intelligence (REPORT)

**Status:** Core implemented  
**Developer:** BAHATI GAD WANGWE  
**Migration:** `0083_imaging_intelligence`

## Capabilities

| Feature | Behaviour |
|---------|-----------|
| **Contrast safety** | Pre-order check vs active allergies (iodine/gadolinium); severe → block unless override ≥15 chars |
| **Test safety catalogue** | Contrast type, radiation, pregnancy caution |
| **Critical findings** | Radiologist registers finding → OPEN inbox → clinical ack |
| **TAT** | Order → completed median / p90 |
| **Order gate** | `create_order` runs contrast safety |

### APIs
- `POST /api/v1/imaging-intelligence/contrast-check`
- `PUT /api/v1/imaging-intelligence/test-safety`
- `POST /api/v1/imaging-intelligence/critical-findings`
- `GET /api/v1/imaging-intelligence/critical-findings`
- `POST /api/v1/imaging-intelligence/critical-findings/{id}/acknowledge`
- `GET /api/v1/imaging-intelligence/tat`

Deploy: `alembic upgrade head`

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
