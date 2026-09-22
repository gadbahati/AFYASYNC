# National Phase 10 — Interoperability / HIE Depth (REPORT)

**Status:** Core implemented  
**Developer:** BAHATI GAD WANGWE  
**Migration:** `0085_hie_export_logs`

## Builds on
Existing FHIR-style Patient, AllergyIntolerance, CapabilityStatement endpoints under `/api/v1/interoperability`.

## New

| Feature | Detail |
|---------|--------|
| **Patient $summary** | Document Bundle: Patient + allergies + encounters + medications |
| **Referral package** | Same + optional Composition clinical summary |
| **Export audit** | `hie_export_logs` + `HIE_PATIENT_SUMMARY_EXPORT` audit |
| **Enrollment gate** | Only enrolled patients at the facility |

### APIs
- `GET /api/v1/hie/Patient/{id}/$summary`
- `POST /api/v1/hie/referral-package`
- `GET /api/v1/hie/exports`

Deploy: `alembic upgrade head`

Honest limit: not a full national HIE node; designed to interoperate with DHA HIE using FHIR-shaped documents.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
