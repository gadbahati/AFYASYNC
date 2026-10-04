# Phase 137 — Clinical encounter summary (print-ready)

**Developer:** BAHATI GAD WANGWE

## API

`GET /api/v1/encounters/{encounter_id}/summary`

Returns a single payload for handout / print:

- Facility & patient identity
- Encounter status / times
- Vitals, consultation, diagnoses, procedures, notes
- Clinical orders (Phase 132+)
- Discharge record (if present)

## UI

`EncounterSummaryPanel` on the clinical encounter page with **Print summary** (browser print).

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
