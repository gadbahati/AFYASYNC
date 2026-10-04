# Phase 141 — Full router registry + worklist navigation

**Developer:** BAHATI GAD WANGWE

## Backend

Router CSV parts (full platform coverage):

| File | Content |
|------|--------|
| `routers.csv` | Core clinical + claims + portal (45) |
| `routers_1.csv` | National ops, HIE, consent, telemedicine (45) |
| `routers_2.csv` | Financing intelligence + auth + worklist (46) |

`router_registry.py` loads all parts, de-duplicates by alias, and `main_application` mounts each.

## Frontend

- Dashboard hero + operational areas → **Clinical worklist** (`/clinical-worklist`)
- Worklist page: `ClinicalWorklistPage.tsx`

## App.tsx restore (if still slim)

```bash
bash scripts/restore_app_tsx.sh
git add frontend/src/App.tsx && git commit -m "restore full App.tsx + clinical-worklist" && git push
```

Good source commit: `b7e5a318802fa625a0fd780f978b43389df1f341`

## Verify

```bash
curl -s "$API/ready" | jq '.data.routers_mounted | length'
# open /clinical-worklist after facility login
```

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
