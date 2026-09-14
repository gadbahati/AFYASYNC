# AfyaSync Engineering Gap Closure

This file separates what source code can close from what requires an external deployment, regulator, payer, telecom provider or pilot.

| Area | Engineering position | External gate |
|---|---|---|
| Core architecture | Implemented foundation | Production architecture review |
| Backend foundation | Implemented foundation | Production infrastructure |
| Basic clinical workflows | Broad module coverage | Clinical workflow validation and accreditation |
| Financing foundation | Multi-payer/claims foundation | Payer contract and tariff validation |
| National architecture | National-scoped services and reporting | Government operating model |
| Frontend | Production-oriented React application | UX/accessibility/UAT |
| Security baseline | Hardened headers, error handling, auth abuse controls, audit and facility isolation | Independent penetration test and remediation |
| Automated testing | Backend CI/test suite and regression coverage | Required coverage/UAT thresholds for pilot |
| SHA production integration | Adapter boundary exists; official operations must be mapped to provider contracts/specs | SHA credentials, certification/acceptance, production access |
| FHIR/interoperability | FHIR-shaped clinical exchange and DHIS2 export foundation | Endpoint/version/profile conformance and receiving-system acceptance |
| Offline operation | Offline web application shell implemented; API/PHI intentionally not cached | Safe offline clinical transaction/sync design and field validation |
| USSD | Signed provider-neutral callback boundary implemented | Telecom/aggregator contract, shortcode, member authentication and service approval |
| Supply chain | National supply planning/capacity foundation | Real catalogue, supplier, stock and procurement integrations |
| Advanced clinical modules | Backend domain modules exist for multiple specialties | Clinical validation, workflows, devices and UAT |
| National analytics | Aggregate command centre/intelligence foundation | National indicator definitions, data quality and governance |
| Disaster recovery | Recovery architecture/runbook documented; readiness endpoint exists | Managed DB backups, PITR/failover and witnessed restore tests |
| External security testing | Technical baseline prepared for testing | Independent penetration test, remediation and retest |
| Privacy/governance | Technical minimisation/audit rules documented | Data protection impact assessment, contracts, notices and governance |
| Government certification/adoption | No source-code shortcut is possible | Formal government/SHA/clinical/accreditation decisions |
| Real-world pilot | Pilot runbook and stop conditions documented | Named facilities, trained users, real infrastructure, approvals and UAT |

## Non-negotiable rule

AfyaSync must never simulate approval, payer eligibility, government certification, clinical accreditation, telecom activation or production transaction outcomes merely to make a feature appear complete. External dependencies are represented as explicit integration boundaries and deployment gates until the authoritative service is connected and acceptance-tested.

## Next execution order

1. Complete automated contract/regression coverage around the new USSD and offline boundaries.
2. Validate FHIR R4/R4B mapping against the exact receiving profiles before enabling exchange.
3. Add real DHIS2 orgUnit/data-element mapping as deployment configuration, not hard-coded facility UUIDs.
4. Build a conflict-safe offline clinical workflow only after defining the approved offline data set and sync authority.
5. Connect official SHA operations only from supplied credentials/specifications and verify each operation end-to-end.
6. Execute backup/restore and failover tests in the actual production-like environment.
7. Commission independent penetration testing and remediate findings.
8. Complete privacy governance and pilot/UAT gates before real patient use.
