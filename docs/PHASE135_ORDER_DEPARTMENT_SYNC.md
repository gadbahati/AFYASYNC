# Phase 135 — Clinical order ↔ department completion sync

**Developer:** BAHATI GAD WANGWE

## Purpose

When a forwarded order finishes in the department, the clinical order auto-completes.

| Source | Trigger | Effect |
|--------|---------|--------|
| Lab | `verify_result` | Clinical LAB orders linked in notes → COMPLETED |
| Pharmacy | `dispense_prescription` | Clinical PHARMACY orders → COMPLETED |
| Manual | `POST .../orders/{id}/sync` | Re-check linked lab/Rx status |

Linkage uses notes written in Phase 134:

```
linked_lab_order=<uuid>
linked_prescription=<uuid>
```

## API

`POST /api/v1/encounters/orders/{order_id}/sync`

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
