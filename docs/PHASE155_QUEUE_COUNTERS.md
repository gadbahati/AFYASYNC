# Phase 155 — Clinical queue counters

**Developer:** BAHATI GAD WANGWE

## Component

`ClinicalQueueStrip` loads:

- `GET /api/v1/clinical/worklist?order_type=LAB`
- `…PHARMACY`
- `…IMAGING`

Shows open counts + links to worklist / radiology.

## Integration

Add to facility dashboard:

```tsx
import { ClinicalQueueStrip } from "../components/ClinicalQueueStrip";
// inside JSX after hero:
<ClinicalQueueStrip />
```

Worklist can read `?type=` from URL (optional enhancement).

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
