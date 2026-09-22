# National Phase 10 — HIE / Interoperability (ROBUST)

**Developer:** BAHATI GAD WANGWE  
**Migrations:** `0085_hie_export_logs`, `0086_hie_robust`

## Why this exists
SHA and DHA already own national claims and HIE direction. AfyaSync cannot “win” by a thinner feature list. It must be a **certifiable, interoperable operating layer** hospitals and government can run with real audit, consent, and exchange discipline.

## Full capability set

| Layer | What it does |
|-------|----------------|
| **Outbound summary** | FHIR document Bundle: Patient, allergies, encounters, meds, **lab Observations** |
| **Referral package** | Summary + Composition clinical note + purpose-of-use |
| **Inbound validation** | Accept/reject partner Bundles with structured errors |
| **Trusted nodes** | Registry of facilities / gateways with trust level |
| **Purpose of use** | TREATMENT · PAYMENT · PUBLICHEALTH · OPERATIONS |
| **Consent redaction** | Sensitive disclosure driven by `consent_given` |
| **Audit** | Export + inbound logs + audit actions |
| **CapabilityStatement** | `GET /api/v1/hie/metadata` |

## APIs
- `GET /api/v1/hie/metadata`
- `GET /api/v1/hie/Patient/{id}/$summary`
- `POST /api/v1/hie/referral-package`
- `POST /api/v1/hie/inbound`
- `PUT|GET /api/v1/hie/nodes`
- `GET /api/v1/hie/exports`

## Deploy
`alembic upgrade head`

## Honest national posture
AfyaSync is built to **interoperate with** DHA HIE and SHA claims rails—not to pretend those rails do not exist. Strength is hospital OS + citizen controls + claim quality + exchange documents with audit.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
