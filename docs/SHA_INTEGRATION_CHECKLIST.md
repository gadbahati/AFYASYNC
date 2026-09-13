# SHA / national payer integration checklist

AfyaSync is ready to plug a **real** SHA (or Taifa Care / SHIF) connector under the existing integration + claims spine.
Until official API docs and credentials exist, use:

- Local membership attach + `verification_status`
- Coverage simulator (`/api/v1/insight/coverage/simulate`)
- Sandbox reject (`POST /api/v1/claims/{id}/sandbox-reject`) to exercise rejection workbench

## What to search for / request from SHA / MoH / vendor

1. **Eligibility / membership API**
   - Auth method (OAuth2 client credentials, API key, mTLS)
   - Endpoint URL (sandbox + production)
   - Request: membership number / national ID
   - Response: active flag, package, dependants, waiting periods
2. **Benefit / tariff catalogue**
   - Service codes and package limits
3. **Pre-authorization**
   - Create / status / cancel
4. **Claim submission**
   - Payload schema (JSON/XML), idempotency, batch vs single
5. **Claim status / callbacks**
   - Webhook signature scheme (map to existing `X-AfyaSync-Signature` style or adapter)
6. **Remittance / payment advice**
7. **Error / rejection code list** (map into `app/claims/rejection_guide.py`)

## Where to wire in AfyaSync (do not redesign)

| Concern | Module |
|---------|--------|
| Credentials & outbound queue | `app/integrations/` |
| Claim create / validate / submit / response | `app/claims/service.py` |
| Local coverage attach | `app/coverage/` |
| Eligibility UX | Reception SHA lookup + simulator |
| Rejection UX | `/api/v1/claims/workbench/rejections` |

## Adapter contract (target)

Implement a provider class, e.g. `ShaPayerAdapter`:

- `verify_member(membership_number) -> EligibilityResult`
- `submit_claim(payload) -> SubmitResult`
- `parse_callback(headers, body) -> PayerResponse`

Register as `Integration` with `provider="SHA"`, `integration_type="PAYER_CLAIMS"`.

## Security

- Never hardcode secrets in the repo
- Store secrets in env / secret manager
- Log request IDs, not full PHI payloads
