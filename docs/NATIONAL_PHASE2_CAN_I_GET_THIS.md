# National Phase 2 — Coverage & Benefits + “Can I Get This?” (REPORT)

**Status:** Core implemented  
**Developer:** BAHATI GAD WANGWE  
**Migration:** `0079_benefit_utilisation`

---

## Killer feature

`POST /api/v1/coverage/can-i-get-this`

Ask: *Can this person get service X at this price?*

Returns:
- eligible / covered
- remaining benefit + YTD utilisation
- authorisation required?
- expected payer amount(s) with coordination of benefits
- patient responsibility
- cash fallback
- documents required
- facility requirements
- per-payer messages

Supports `as_of` date for **historical rule reconstruction** (Phase 13 foundation).

---

## Built

| Capability | Delivery |
|------------|----------|
| Eligibility | ACTIVE + date window + verification |
| Benefit rules | percent, copay, max, exclusion, preauth, annual limit |
| Utilisation | `benefit_utilisation` ledger + post API |
| Multi-payer | Ranked coordination primary/secondary |
| Patient responsibility | Residual after payer stack |
| Documents | From rule JSONB + preauth default |
| Audit | `CAN_I_GET_THIS` |

Existing OOP estimate and benefit packages remain; this phase adds the **interrogation** product surface.

---

## Hardening checklist (before Phase 3)

| Case | Expected |
|------|----------|
| Expired coverage | eligibility EXPIRED, no payer share |
| Overlapping coverages | primary then secondary absorb |
| Exhausted annual limit | remaining 0, patient pays |
| Excluded service | covered false |
| Preauth required | requires_authorisation true |
| Zero price probe | still returns eligibility/docs |
| Deceased person | 409 |

Deploy: `alembic upgrade head`.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
