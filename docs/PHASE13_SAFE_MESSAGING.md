# Phase 13 — Template-only safe patient messaging (HARDENED)

**Developer:** BAHATI GAD WANGWE  
**Status:** Implemented + hardened

---

## Rule

**Patients cannot free-type** into facility threads. They pick an approved template and fill constrained slots only.

Facility staff **prefer templates**; short free-text (≤500 chars) remains available for clinical coordination.

---

## Catalog (examples)

**Patient:** APPT_FOLLOW_UP, CHANGE_PREFERRED_DATE, CONFIRM_ATTENDANCE, NEED_RESCHEDULE, LAB_RESULTS_QUERY, MEDICATION_QUERY, BRING_DOCUMENTS, GENERAL_CARE_HELP  
**Facility:** FACILITY_ACK, FACILITY_APPT_REMINDER, FACILITY_BRING_ID, FACILITY_RESULTS_READY, FACILITY_CALL_RECEPTION, FACILITY_OFFER_SLOT

---

## APIs

| Route | Notes |
|-------|--------|
| `GET /api/v1/portal/messages/templates` | Patient catalog |
| `POST /api/v1/portal/messages` | Requires `template_code` (+ slots) |
| `GET /api/v1/facility/messages/templates` | Staff catalog |
| `POST /api/v1/facility/messages` | `template_code` or short `body` |

Migration: `0074_message_templates` (`template_code` column).

---

## Hardening

| Control | Detail |
|---------|--------|
| Allow-list | Unknown template → `UNKNOWN_TEMPLATE` |
| Slots | Required, max length, no control chars |
| Rate limit | 20 patient messages / hour / facility |
| Audit | `template_code` on send |
| No free patient body | `TEMPLATE_REQUIRED` if missing |

---

## Deploy

```bash
alembic upgrade head
```

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
