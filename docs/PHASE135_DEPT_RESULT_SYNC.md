# Phase 135 — Department result → clinical order sync

**Developer:** BAHATI GAD WANGWE

## Problem fixed

`backend/app/laboratory/service.py` and `backend/app/pharmacy/service.py` were **empty (0 bytes)** on main, which would crash lab/pharmacy API routes on import.

## Restored

### Laboratory service
- `create_test`, `create_order`, `collect_sample`, `receive_sample`, `enter_result`, `verify_result`, `forward_order_to_prescription`

### Pharmacy service
- `PharmacyError`, `dispense_prescription` (stock movement + status)

## Clinical sync (new)

On **lab result verify** and **pharmacy dispense**:

1. Match clinical orders by linked id in notes (`linked_lab_order=` / `linked_prescription=`)
2. Also complete open `LAB` / `PHARMACY` clinical orders on the same encounter
3. Append `[DEPT_RESULT] …` notes and set status `COMPLETED`
4. Audit `CLINICAL_ORDER_DEPT_SYNC`

Module: `app.clinical.result_sync`

## Flow

```
Clinical order → Forward (134) → Lab/Pharmacy work
  → Verify result / Dispense
  → Clinical order auto-COMPLETED with result notes
```

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
