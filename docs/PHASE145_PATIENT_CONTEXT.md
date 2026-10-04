# Phase 145 — Patient context on worklist

**Developer:** BAHATI GAD WANGWE

## Backend

`order_to_dict` already returns `patient_id` (no API change required).

## Frontend

Deep-links now include:

```
?patientId=&encounterId=&orderId=
```

| Type | Path |
|------|------|
| LAB | `/laboratory?patientId&encounterId&orderId` |
| PHARMACY | `/pharmacy?patientId&encounterId&orderId` |
| IMAGING | `/radiology?patientId&encounterId&orderId` |

Worklist and radiology rows also expose **Patient** and **Encounter** shortcuts.

Lab page already reads `patientId` / `encounterId`. Pharmacy already reads `patientId`.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
