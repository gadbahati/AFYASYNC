# Phase 136 — Encounter discharge UI

**Developer:** BAHATI GAD WANGWE

## Purpose

Surface Phase 131 discharge APIs on the clinical encounter record so clinicians can close the visit without leaving the page.

## UI

`EncounterDischargePanel` on `EncounterDetailPage`:

- Load existing discharge (`GET /api/v1/encounters/{id}/discharge`)
- Form: disposition, outcome, follow-up date/instructions, summary
- Submit → `POST /api/v1/encounters/{id}/discharge`
- Reloads clinical timeline after success

## Dispositions

HOME · TRANSFER · ADMIT · REFERRED · LEFT_AMA · ABSCONDED · DIED

## Outcomes

STABLE · IMPROVED · WORSENED · DECEASED · UNKNOWN

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
