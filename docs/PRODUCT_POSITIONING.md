# AfyaSync product positioning

## One-line

AfyaSync is a **standalone** facility health platform. People can register on AfyaSync. It also **accepts SHA members** without forcing AfyaSync membership, and always supports **cash / uninsured** patients.

## Paths

| Mode | Meaning |
|------|---------|
| `AFYASYNC` | Optional AfyaSync membership / benefits |
| `SHA` | National SHA cover accepted; no AfyaSync membership required |
| `CASH` | Self-pay |
| `OTHER` | Corporate / other third-party |

## Staff reception flows

1. **No SHA** → **Register patient** (`/patients/new`) → open encounter as CASH or enroll AfyaSync cover.
2. **Has SHA** → **SHA member lookup** (`/patients/sha-lookup`) by membership number → open patient / encounter with SHA cover. No AfyaSync membership forced.
3. **Cash always** → encounter `coverage_mode=CASH` → invoice/payment only; **claims are blocked** for cash encounters.

## Identity vs coverage

- **Person / facility patient** = clinical identity at the facility  
- **AfyaIdentity (`afya_id`)** = platform identifier  
- **Coverage row** = payer link (AFYASYNC / SHA / CASH / OTHER)  
- These must not be collapsed into “must be SHA” or “must be AfyaSync member”

## Encounter + claims rules

- Every encounter stores `coverage_mode` (and optional `coverage_id`).
- Claims require verified payer coverage.
- `CASH` encounters cannot create claims (`CASH_ENCOUNTER_NO_CLAIM`).
- `SHA` mode claims require a SHA-family payer; `AFYASYNC` mode requires AfyaSync payer.

## What we are not

- Not a project whose goal is to legally replace the Social Health Authority  
- Not SHA-only  
- Not unable to run without SHA  
