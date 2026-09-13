# AfyaSync Beast Roadmap

Positioning: **facility operating system + multi-payer pay + insight** — not a SHA clone.
Standalone first. SHA accepted via lookup. Cash always works.

## Shipped in Insight layer (this phase)

| Capability | API | UI |
|------------|-----|----|
| Coverage simulator | `POST /api/v1/insight/coverage/simulate` | `/coverage-simulator` |
| Command centre | `GET /api/v1/insight/command-centre` | `/command-centre` |
| Fraud radar | `GET /api/v1/insight/fraud-radar` | `/command-centre` |

Also live-wired: pharmacy, billing, claims list UIs; multi-coverage spine (`AFYASYNC|SHA|CASH|OTHER`).

## Next (priority)

1. Production API deploy + remove demo bypass for live
2. Official SHA eligibility connector (sandbox → production)
3. Claim rejection workbench (guided fix + resubmit)
4. Tariff / package rules feeding the simulator
5. County aggregate command centre
6. Offline facility core
7. Member USSD
8. DHIS2 export
9. Theatre / maternity / ICU UI depth to match backend modules

## Demo script (15 min)

1. Command centre metrics
2. Coverage simulator (SHA vs cash)
3. Register / SHA lookup
4. Encounter → clinical → lab → pharmacy → invoice
5. Claim create / validate
6. Fraud radar scan
