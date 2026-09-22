# National Phase 15 — Supply Chain & National Logistics Depth

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## APIs

| Path | Purpose |
|------|---------|
| `GET /api/v1/logistics/stockout-board` | County/national at-risk SKUs |
| `GET /api/v1/logistics/redistribution` | Surplus → deficit suggestions |
| `GET /api/v1/logistics/facility-health` | Single-facility risk profile |

Builds on existing `/api/v1/national-supply/*` and pharmacy FEFO/controlled log.

## Honest limit
Redistribution is **advisory** — does not move stock without facility approval workflows.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
