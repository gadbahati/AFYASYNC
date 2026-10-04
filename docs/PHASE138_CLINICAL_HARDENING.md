# Phase 138 — Clinical path hardening

**Developer:** BAHATI GAD WANGWE

## Fixes

1. **Timeline facility_id** — `get_encounter_clinical_summary(db, encounter_id, facility_id)` was called with 2 args; now passes facility context.
2. **Path aliases**
   - `/clinical` → same as `/clinical-timeline`
   - `/clinical-notes` → same as `/notes`
3. **Service guard module** — `path_hardening.assert_department_services_loaded()` detects empty lab/pharmacy service files.
4. **Client** — `closeEncounter` → `POST /api/v1/encounters/{id}/close`

## Contract

See `app.clinical.path_hardening.CLINICAL_PATH_CONTRACT`.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
