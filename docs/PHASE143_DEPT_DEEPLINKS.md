# Phase 143 — Department deep-links from worklist

**Developer:** BAHATI GAD WANGWE

## Mapping

| Order type | Department link |
|------------|-----------------|
| LAB | `/laboratory` — Lab workbench |
| PHARMACY | `/pharmacy` — Pharmacy |
| IMAGING | `/laboratory` — Imaging / diagnostics (until dedicated radiology UI route is restored) |

## Row actions (from Phase 142–143)

1. **Encounter** — clinical record
2. **Dept deep-link** — workbench for that order type
3. **Forward to dept** — `POST .../orders/{id}/forward`
4. **Mark complete** — `POST .../orders/{id}/fulfill`

## Note

Restore full `App.tsx` if routes are slim so `/laboratory` and `/pharmacy` resolve:

```bash
bash scripts/restore_app_tsx.sh && git add frontend/src/App.tsx && git commit -m "restore App routes" && git push
```

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
