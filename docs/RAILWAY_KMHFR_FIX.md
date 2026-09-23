# Railway: stop KMHFR log spam

## Why you still see the spam

Active deployment **`backend/858a01e9` (2026-09-22)** is **old code**.

The fix is on GitHub `main` (commit message: *Fix KMHFR log spam*).  
**Railway has not deployed that commit yet.** Until you redeploy, logs will keep repeating.

## Do this now (2 minutes)

### 1. Add variable (stops retries even on old code if you patch — on new code it fully disables)

Railway → **backend** → **Variables** → Add:

| Name | Value |
|------|--------|
| `KMHFR_SYNC_ENABLED` | `0` |

### 2. Redeploy latest `main`

Railway → **backend** → **Deployments** → **Deploy** / **Redeploy** from latest GitHub `main`  
(or push any empty commit if auto-deploy is on).

You must see a **new** deployment ID **after 2026-09-23**, not `858a01e9`.

### 3. Confirm

- Deploy logs: at most **one** `KMHFR_SNAPSHOT_UNAVAILABLE` per hour (or none if disabled)
- `https://backend-production-8132.up.railway.app/health` → healthy
- `https://backend-production-8132.up.railway.app/ready` → ready

## What the spam means

Not a crash. Missing file `data/kmhfr_facilities.json` on the server.  
App keeps working with **local** facility data.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
