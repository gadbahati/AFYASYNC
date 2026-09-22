# SHA / DHA AfyaLink Integration

**Developer:** BAHATI GAD WANGWE  
**Package:** `backend/app/sha_dha/`

## Research basis (public sources)

| Capability | Public endpoint pattern | Source |
|------------|-------------------------|--------|
| Eligibility (SHIF/ECCIF) | `GET {{base}}/v2/eligibility` | afyalink.dha.go.ke apidocs |
| Claim submit | `POST {{base}}/v1/shr-med/bundle` | Claims Submission Guide / SHR Mediator |
| Claim status | `GET {{base}}/v1/shr-med/claim-status` | same |
| Preauth | FHIR Bundle to same SHR mediator | SHA Portal Preauth guide |
| UAT base | `https://uat.dha.go.ke` | public API samples |
| Credentials | developer.dha.go.ke / facility onboarding | AfyaLink wiki |
| Certification | certification.dha.go.ke | DHA |

Also: Kenya eClaims FHIR IG (DHA + SHA), Social Health Insurance Regulations (claims via Centralized Digital Platform within 7 days of discharge).

## AfyaSync APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/sha-dha/status` | Mode + credential readiness |
| POST | `/api/v1/sha-dha/eligibility` | Membership eligibility |
| POST | `/api/v1/sha-dha/claims/{id}/submit` | Build FHIR-shaped bundle + submit |
| GET | `/api/v1/sha-dha/claims/status?bundle_id=` | Poll status |

## Environment

```bash
# Offline / pilot wiring (default)
SHA_DHA_MODE=mock

# Live (after you obtain facility credentials)
SHA_DHA_MODE=live
AFYALINK_BASE_URL=https://uat.dha.go.ke   # or production base from DHA
AFYALINK_BEARER_TOKEN=your_token
AFYALINK_AGENT=YOUR_AGENT_CODE
```

## Full truth

- **You cannot complete live SHA calls without official credentials.** Those are issued per facility after contracting / developer onboarding.
- Mock mode is **explicit** (`mode: mock` in responses) so the rest of the hospital OS keeps working offline.
- Bundle shape follows public AfyaLink samples (Organization, Coverage, Patient, Claim).
- Intervention codes must map to SHA benefits catalogue (tariffs spreadsheet) for clean claims.

## Next operational steps for you

1. Register system on [developer.dha.go.ke](https://developer.dha.go.ke) / AfyaLink  
2. Obtain sandbox then production Bearer token  
3. Map local service codes → SHA intervention codes  
4. Set env vars, set `SHA_DHA_MODE=live`  
5. Apply for [DHA certification](https://certification.dha.go.ke/)  

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
