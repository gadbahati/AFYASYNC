# National Phase 3 — Afya Citizen Super-Portal (REPORT)

**Status:** Core implemented  
**Developer:** BAHATI GAD WANGWE  
**Migration:** `0080_patient_complaints`

---

## Citizen capabilities added

| Feature | API | UI |
|---------|-----|-----|
| My Health Timeline | `GET /api/v1/portal/citizen/timeline` | Afya Citizen tabs |
| Who Accessed My Record | `GET .../access-history` | Yes |
| Why Was I Charged | `GET .../charges` | Yes |
| Emergency Summary | `GET .../emergency-summary` | Yes |
| My Documents | `GET .../documents` | Continuity cards |
| That Wasn't Me / Report | `POST/GET .../complaints` | Yes |

Route: **`/portal/citizen`** (patient session).

Existing portal retained: visits, consents, coverage, booking, messages, continuity card.

Bugfix: portal coverage list now uses `Coverage.person_id`.

---

## Hardening notes

- Patient identity required on all citizen routes
- Access history scoped to `patient_id` on audit log
- Charge explain is patient-scoped invoices/charges
- Complaints require min description length
- Emergency summary disclaimer; sensitive clinical detail still governed by facility consent rules

Deploy: `alembic upgrade head`

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
