# SHA EDI connector

AfyaSync treats SHA as an authorised external payer integration, not as a built-in fake or simulator. The live connector is fail-closed: without an active facility integration, the system does not report a successful SHA eligibility result or claim submission.

## Official endpoints

SHA currently exposes its EDI service on SHA-owned domains. The public EDI landing page is available at `https://api-edi.provider.sha.go.ke/`; the UAT environment is `https://edi-api.provider-uat.sha.go.ke/`; and the development environment is `https://edi-api.provider-dev.sha.go.ke/`. These environments are visible from the SHA API service itself; exact operation paths and credentials must be obtained from SHA and must not be guessed by AfyaSync.

## Configure a facility integration

Create an active facility integration with:

```json
{
  "adapter_type": "sha_edi",
  "endpoint": "https://edi-api.provider-uat.sha.go.ke/<SHA-supplied-operation-path>",
  "credential_env": "SHA_UAT_TOKEN",
  "timeout_seconds": 20
}
```

Use `api-edi.provider.sha.go.ke` and a SHA-supplied production operation path for production. The secret itself is never stored in the database; `credential_env` names the environment variable containing the credential.

The connector rejects non-HTTPS endpoints and non-SHA hosts. It also carries an idempotency key for outbound requests and treats transport failures and HTTP 429/5xx responses as retryable.

## Eligibility contract

The existing eligibility workflow sends an `ELIGIBILITY_CHECK` operation with the AfyaSync ID and normalized SHA membership number. A successful response must contain a boolean `eligible`; optional membership, plan and coverage dates are validated before AfyaSync persists the coverage result.

AfyaSync does **not** invent SHA response mappings. If SHA changes its operation schema, update the connector mapping from the authoritative SHA specification before enabling the integration.

## Production activation gate

Before activating a live facility integration:

1. Confirm the facility is appropriately empanelled/contracted with SHA.
2. Obtain the SHA-issued production endpoint, credentials and operation contract.
3. Configure the secret in the deployment secret store, not Git.
4. Test the integration in SHA UAT first.
5. Verify signed callbacks and idempotent retries where applicable.
6. Activate the production integration only after the authorised SHA onboarding process is complete.

Healthcare workflows remain usable when SHA is unavailable; the system records an unavailable/retryable integration state rather than fabricating eligibility.
