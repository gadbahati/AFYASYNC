# National Phase 4 — Afya Hospital OS (REPORT)

**Status:** Core spine implemented  
**Developer:** BAHATI GAD WANGWE

---

## What this phase delivers

Hospital OS does **not** replace existing clinical modules. It **orchestrates and hardens** them into one encounter spine with orphan prevention.

### Journey stages (per encounter)

Registration → Encounter → Vitals → Consultation → Diagnosis → Lab → Radiology → Pharmacy → Charges → Invoice → Claim

`GET /api/v1/hospital-os/encounters/{id}/journey` returns stage completion, next recommended step, blockers, integrity flag.

### Integrity scan

`GET /api/v1/hospital-os/integrity` scans recent facility encounters for:
- charge / prescription patient mismatch
- invoice without charges
- claim linkage issues

### Claim gate

`create_claim` now runs `assert_can_create_claim_for_invoice` (Hospital OS) before existing claim rules — invoice must belong to facility with valid encounter and claimable patient.

Existing modules (encounters, clinical, lab, pharmacy, billing, claims, wards, theatre, admissions) remain the operational systems of record.

---

## Hardening checklist

| Check | Status |
|-------|--------|
| No claim without invoice/encounter | Gated |
| Journey visibility for staff | API |
| Orphan scan | API |
| Full UI journey board | Deferred (use API + existing pages) |
| Automated E2E simulation suite | Next hardening pass |

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
