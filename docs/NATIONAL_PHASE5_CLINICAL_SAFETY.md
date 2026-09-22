# National Phase 5 — Clinical Safety Engine (REPORT)

**Status:** Core implemented  
**Developer:** BAHATI GAD WANGWE  
**Migration:** `0081_medication_safety_flags`

---

## Prescribe-Time Safety Intercept

Before a prescription is finalised, the system runs:

| Check | Behaviour |
|-------|-----------|
| Cross-facility allergies | CRITICAL/HIGH can **block** |
| Drug–drug interactions | HIGH **block** (override ≥15 chars) |
| Duplicate therapy | Warning |
| Black-box / high-risk flags | Warning |
| Paediatric caution (age < 12) | Warning |
| Pregnancy category D/X | X **blocks**; D high |
| Renal caution | Warning |

### APIs
- `POST /api/v1/clinical-safety/check`
- `PUT /api/v1/clinical-safety/flags` — formulary safety attributes
- Existing pharmacy create path uses `assert_can_create_prescription` → Clinical Safety Engine

### Audit
`CLINICAL_SAFETY_CHECK`, `CLINICAL_SAFETY_OVERRIDE`

Deploy: `alembic upgrade head`

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
