# Phase 140 — Main restore + worklist route

**Developer:** BAHATI GAD WANGWE

## Main.py recovery

1. Full application source is rebuilt from commit `dede4b53` + Phase 139 hooks (worklist router, clinical startup, `/ready` clinical_departments).
2. Loader: `main.py` → `main_restore.install_into` → gzip+base64 parts `_main_blob_*.b64`.
3. Fallback: `main_application.py` mounts core routers if blob restore fails.

## Frontend

- Route `/clinical-worklist` → `ClinicalWorklistPage`

## Verify

```bash
curl -s $API/ready | jq .data.clinical_departments
curl -s -H "Authorization: Bearer $TOKEN" $API/api/v1/clinical/worklist?order_type=IMAGING
```

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
