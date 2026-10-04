# Phase 148 — Full App route tree restore

**Developer:** BAHATI GAD WANGWE

## Why

`App.tsx` was reduced to a slim clinical subset. The full platform needs claims, referrals, national modules, MCH, etc.

## Restore (on your machine with git)

```bash
python3 scripts/merge_app_routes.py
git add frontend/src/App.tsx
git commit -m "Phase 148: restore full App.tsx with worklist/radiology"
git push
```

This loads `frontend/src/App.tsx` from commit `b7e5a318` and ensures:

- `/clinical-worklist` → `ClinicalWorklistPage`
- `/radiology` → `RadiologyPage`
- Existing `/laboratory` and `/pharmacy` from the full tree

## Current slim App (until you run the script)

Still has: dashboard, patients, encounters, worklist, laboratory, pharmacy, radiology.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
