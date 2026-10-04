# Phase 132 — Clinical orders (LAB / PHARMACY / IMAGING)

**Developer:** BAHATI GAD WANGWE

## Purpose

Place orders on an **open** encounter after triage/consultation (Phases 128–130), before or alongside discharge (131).

## API

| Method | Path |
|--------|------|
| GET | `/api/v1/encounters/{id}/orders` |
| POST | `/api/v1/encounters/{id}/orders` |
| PATCH | `/api/v1/encounters/orders/{order_id}/status` |

### Create body

```json
{
  "order_type": "LAB",
  "code": "CBC",
  "description": "Complete blood count",
  "priority": "ROUTINE",
  "notes": "Fasting not required"
}
```

**Types:** LAB, PHARMACY, IMAGING  
**Priority:** ROUTINE, URGENT, STAT  
**Status:** ORDERED → IN_PROGRESS → COMPLETED | CANCELLED

Closed/discharged encounters reject new orders (`ENCOUNTER_CLOSED`).

## Migration

`0131_clinical_orders`

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
