# Phase 140 — Main bootstrap + App recovery

**Developer:** BAHATI GAD WANGWE

## Backend (done)

- `main.py` → `main_application.app`
- `router_registry.py` loads `routers.csv` + `routers_more.csv`
- Core clinical, auth, encounters, lab, pharmacy, radiology, claims, worklist mounted
- `/ready` reports `routers_mounted` / `routers_failed` and `clinical_departments`

## Frontend — ACTION REQUIRED

`App.tsx` was briefly replaced with a slim route tree. Restore the full tree:

```bash
bash scripts/restore_app_tsx.sh
git add frontend/src/App.tsx && git commit -m "restore full App.tsx with clinical-worklist route"
```

Or manually:

```bash
git show b7e5a318802fa625a0fd780f978b43389df1f341:frontend/src/App.tsx > frontend/src/App.tsx
# add import ClinicalWorklistPage and route path="/clinical-worklist"
```

Worklist page component remains at `frontend/src/pages/ClinicalWorklistPage.tsx`.

## Verify

```bash
curl -s "$API/ready" | jq '.data.routers_mounted,.data.clinical_departments'
curl -s -H "Authorization: Bearer $TOKEN" "$API/api/v1/clinical/worklist?order_type=IMAGING"
```

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
