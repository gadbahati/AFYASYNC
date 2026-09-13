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

## Identity vs coverage

- **Person / facility patient** = clinical identity at the facility  
- **AfyaIdentity (`afya_id`)** = platform identifier  
- **Coverage row** = payer link (AFYASYNC / SHA / CASH / OTHER)  
- These must not be collapsed into “must be SHA” or “must be AfyaSync member”

## Encounter rule

Every encounter stores `coverage_mode` (and optional `coverage_id`).
Billing and claims should branch from that mode and the linked payer.

## What we are not

- Not a project whose goal is to legally replace the Social Health Authority  
- Not SHA-only  
- Not unable to run without SHA  
