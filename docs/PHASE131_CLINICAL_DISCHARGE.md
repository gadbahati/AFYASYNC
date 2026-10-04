# Phase 131 — Clinical encounter discharge

**Developer:** BAHATI GAD WANGWE

## Purpose

Close the clinical lifecycle after Phase 128–130 (triage → consultation → procedures/notes):

```
OPEN encounter → clinical work → DISCHARGE → status DISCHARGED + ended_at
```

## API

| Method | Path |
|--------|------|
| POST | `/api/v1/clinical/encounters/{id}/discharge` |
| GET | `/api/v1/clinical/encounters/{id}/discharge` |

### Body

```json
{
  "disposition": "HOME",
  "outcome": "IMPROVED",
  "follow_up_instructions": "Return in 7 days if fever persists",
  "follow_up_date": "2026-10-11",
  "discharge_summary": "OPD review complete…"
}
```

**Dispositions:** HOME, TRANSFER, ADMIT, LEFT_AMA, DIED, ABSCONDED, REFERRED  
**Outcomes:** STABLE, IMPROVED, WORSENED, DECEASED, UNKNOWN

## Migration

`0130_clinical_discharge` → table `clinical_discharges`

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
