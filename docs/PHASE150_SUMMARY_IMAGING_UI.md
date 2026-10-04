# Phase 150 — Imaging reports on encounter summary UI

**Developer:** BAHATI GAD WANGWE

## UI

`EncounterSummaryPanel` now renders `summary.imaging_reports`:

- Modality
- Code / description
- Impression (primary)
- Fallback to raw notes

Print (`window.print`) includes this section via `#clinical-summary-print`.

## Flow

```
Radiology Complete study (modality + impression)
  → fulfill API
  → order notes + clinical note
  → GET .../summary → imaging_reports[]
  → Summary panel + Print
```

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
