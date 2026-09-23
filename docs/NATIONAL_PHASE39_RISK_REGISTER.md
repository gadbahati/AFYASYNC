# National Phase 39 — Security Residual Risk Register & Residual Controls

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## APIs

| Path | Purpose |
|------|---------|
| `POST /api/v1/risk-register/seed` | Seed default residual risks |
| `GET /api/v1/risk-register/posture` | Composite residual risk band |
| `GET /api/v1/risk-register/risks` | List risks |
| `PATCH /api/v1/risk-register/risks/{id}` | Update status/controls |

**Migration:** `0096_residual_risks`

## Honest limit
Documents residual risk — does not eliminate it. Acceptances need accountable owners.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
