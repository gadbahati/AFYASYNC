# Patient-Controlled Sensitive Disease Disclosure

**Developed by Bahati GAD Wangwe**

## Purpose

Some diagnoses are highly sensitive (HIV, mental health, certain STIs, GBV-related findings, substance use). Patients must be able to decide whether that information is visible when they are later searched at another facility.

AfyaSync implements an explicit digital consent step for these diagnoses.

## Rules

1. A diagnosis can be marked `is_sensitive = true`.
2. When a sensitive diagnosis is recorded, the clinician must collect the patient’s explicit consent on screen (digital signature or equivalent).
3. The consent is stored in `sensitive_disease_consents` with:
   - `consent_given` (true / false)
   - `share_scope` (`CROSS_FACILITY` or `FACILITY_ONLY`)
   - signature proof, timestamp, facility, and clinician
4. **Cross-facility visibility**:
   - Only diagnoses with an active consent where `consent_given = true` and `share_scope = CROSS_FACILITY` may appear when the patient is looked up at another facility.
   - If the patient declines, or if no consent record exists, the diagnosis remains **facility-local** and must not be returned in cross-facility searches.
5. All consent decisions are audited.

## API

- `POST /api/v1/consent/sensitive-disease` — record patient consent + signature
- `GET /api/v1/consent/sensitive-disease/check/{diagnosis_id}?patient_id=...` — check whether a diagnosis may be shared
- `GET /api/v1/consent/sensitive-disease/patient/{patient_id}` — list consents for a patient at the current facility

## Default sensitive categories

Seeded categories (code):

- `HIV` — HIV / AIDS related
- `MENTAL_HEALTH` — Mental health
- `STI` — Sexually transmitted infections
- `GBV` — Gender-based violence related
- `SUBSTANCE` — Substance use disorders

These can be extended via the `sensitive_categories` table.

## Clinical workflow (target)

1. Clinician records diagnosis and marks it as sensitive (or system auto-flags by category).
2. System presents on-screen consent form to the patient.
3. Patient signs / confirms Yes or No.
4. Consent is stored; diagnosis becomes shareable only if the patient agreed.

## Legal alignment

This design supports Kenya’s Data Protection Act requirements for sensitive personal data and the HIV & AIDS Prevention and Control Act emphasis on informed consent before disclosure.
