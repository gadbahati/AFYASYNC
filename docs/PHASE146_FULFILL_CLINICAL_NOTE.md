# Phase 146 — Fulfillment → encounter clinical note

**Developer:** BAHATI GAD WANGWE

## Behaviour

When `POST /api/v1/encounters/orders/{id}/fulfill` is called with:

- `status`: `COMPLETED`
- `result_notes`: non-empty

the system:

1. Updates the clinical order (existing behaviour)
2. Appends a **FINAL** clinical note on the same encounter:
   - `SPECIALIST` for LAB / IMAGING
   - `PROGRESS` otherwise

So radiology **Complete study** and worklist **Mark complete** surface on:

- Encounter notes
- Clinical timeline / summary (if those aggregate notes)

Note write failures do not roll back order completion.

## Verify

1. Complete an imaging order from `/radiology` with result notes
2. Open encounter → clinical notes / summary shows the fulfillment text

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
