# AfyaSync Privacy & Data Governance

## Purpose

AfyaSync is designed to process health and identity information in a controlled healthcare setting. Technical safeguards are not a substitute for the organisation's legal and governance obligations. Production deployment requires a documented data controller/processor position, lawful processing basis, approved data-sharing arrangements, privacy notices, retention rules, access procedures and accountable governance.

## Data-minimisation rules

- Use the AfyaSync identifier as the application-level person locator; do not expose national identifiers in ordinary clinical responses.
- Keep coverage/financing information separate from person identity and clinical records.
- National, interoperability and payer reads must have an explicit access reason where the workflow requires it and must be auditable.
- Notifications contain minimal operational metadata and must not become a secondary clinical record.
- USSD must not disclose patient information from a phone number alone; member authentication and an approved service catalogue are required before activation.
- Offline browser storage must never cache API responses, access tokens or patient records in the service-worker cache.

## Access and audit

Access is enforced through authenticated users, facility context and explicit permissions. Important identity, interoperability, financing and operational actions are audited. Audit records should be retained according to the approved retention schedule and protected from unauthorised alteration.

## Rights and operational controls

Before a real-world pilot, the operating organisation must document procedures for access requests, correction, objection/restriction where applicable, incident escalation, breach assessment, data-subject communications, account termination and secure disposal/retention. Support staff must not use production clinical data for development or testing.

## Required governance gates before production

1. Identify the responsible data controller(s), processor(s) and sub-processors.
2. Complete the required privacy/data-protection impact assessment for the actual deployment and integrations.
3. Approve a data inventory and classification covering identity, clinical, financial, audit and integration data.
4. Approve retention and deletion schedules for each data class.
5. Approve role/access matrices and periodic access reviews.
6. Execute required data-sharing and processor agreements.
7. Establish an incident-response and breach-notification procedure.
8. Complete independent security testing and remediate findings.
9. Validate cross-border/cloud hosting and vendor arrangements for the actual deployment.
10. Obtain all required clinical, payer, facility, telecom and government approvals before activation.

## Engineering position

The repository implements privacy-oriented technical controls, but it does **not** assert statutory compliance, government certification, SHA approval or ODPC approval. Those are deployment and governance gates outside source code.
