# Phase 134 — Forward clinical orders to departments

**Developer:** BAHATI GAD WANGWE

## Purpose

Connect Phase 132 clinical orders to real department modules:

| Clinical type | Forward target |
|---------------|----------------|
| LAB | `LabOrder` + `LabOrderItem` when `LabTest` matches `code` or name |
| PHARMACY | `Prescription` (+ item when `Medication` matches) |
| IMAGING | Mark IN_PROGRESS for radiology worklist |

## API

`POST /api/v1/encounters/orders/{order_id}/forward`

Requires active **Staff** at the facility for LAB/PHARMACY creation.

### Response

```json
{
  "order": { "id": "...", "status": "IN_PROGRESS", ... },
  "forward": {
    "department": "LAB",
    "matched": true,
    "linked_id": "...",
    "lab_order_id": "LAB-...",
    "message": "..."
  }
}
```

If catalog match fails, clinical order is still moved to worklist notes without a department row.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
