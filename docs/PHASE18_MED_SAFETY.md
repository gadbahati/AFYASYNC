# Phase 18 — Prescribe-time allergy & med safety (HARDENED)

**Developer:** BAHATI GAD WANGWE  
**Status:** Implemented + hardened

---

## Capabilities

| Check | Behaviour |
|-------|-----------|
| Allergy match | Cross-facility ACTIVE allergies vs med name/generic/code |
| Severity | `LIFE_THREATENING` → **hard block** (no override) |
| Severe / interactions | Block unless override ≥15 characters |
| Drug–drug | Conservative high-risk pair list |
| Duplicate therapy | Flags meds already on ACTIVE prescriptions |
| Dispense re-check | Critical allergy blocks dispense even if Rx existed |

## APIs

| Method | Path |
|--------|------|
| `POST` | `/api/v1/pharmacy/safety-check` — dry run |
| `POST` | `/api/v1/pharmacy/prescriptions` — enforces engine |
| `POST` | `/api/v1/pharmacy/prescriptions/{id}/dispense` — re-check |

## Hardening

- Facility-scoped prescribe/dispense  
- Audit: `PHARMACY_SAFETY_CHECK`, block/override events  
- Cross-facility allergy read for safety only (no write)  
- Override reason length enforced  

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
