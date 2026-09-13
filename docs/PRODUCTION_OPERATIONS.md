# AfyaSync Production Operations

## Daily checks

Review API availability, database readiness, worker health, integration queues, failed transactions, and unusual authentication or permission failures.

## Integration incident handling

For a failed integration transaction:

1. Capture the transaction ID and `X-Request-ID` where available.
2. Confirm the integration is still active.
3. Review the response code and attempt count.
4. Confirm the payer endpoint and environment configuration.
5. Allow the retry policy to operate when the failure is transient.
6. Escalate permanent failures for payer/integration review.

Never resolve an operational failure by editing financial or clinical records directly in the database.

## Security incident handling

If credentials or secrets may have been exposed:

1. Disable/rotate the affected credential immediately.
2. Preserve relevant logs and request IDs.
3. Identify affected integrations/accounts.
4. Review audit events.
5. Follow the organisation's incident-response and data-protection process.

## Database recovery

Do not delete clinical or financial history to repair an operational problem. Use the application's audited correction/reconciliation workflows or an approved recovery process.

## Release discipline

Every production release should have a known commit, migration status, rollback decision, smoke-test result, and named owner. Production secrets must remain outside Git.
