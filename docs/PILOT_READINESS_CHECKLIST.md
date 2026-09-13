# AfyaSync Pilot Readiness Checklist

## Governance

- [ ] Data protection/privacy review completed
- [ ] Clinical governance owner identified
- [ ] Security owner identified
- [ ] Facility leadership sign-off completed
- [ ] Required licensing/accreditation/procurement checks completed
- [ ] Payer/integration agreements and technical specifications approved

## Infrastructure

- [ ] Production PostgreSQL provisioned
- [ ] Automated encrypted backups enabled
- [ ] Restore test completed
- [ ] TLS enabled end-to-end
- [ ] API is not publicly exposing the database
- [ ] Production `JWT_SECRET` configured outside Git
- [ ] Exact `CORS_ORIGINS` configured
- [ ] Frontend uses the production API URL
- [ ] API `/health` and `/ready` monitored
- [ ] Integration worker running separately from the API

## Security

- [ ] Least-privilege roles assigned
- [ ] Named staff accounts created
- [ ] No shared credentials
- [ ] Cross-facility isolation tested
- [ ] National permissions tested separately from facility permissions
- [ ] Callback signatures tested
- [ ] Integration secrets verified to be environment-backed
- [ ] Audit trail reviewed
- [ ] Logs reviewed for accidental sensitive-data exposure

## Clinical operations

- [ ] Facility onboarding tested
- [ ] Patient registration tested
- [ ] Encounter and clinical documentation tested
- [ ] Laboratory workflow tested where enabled
- [ ] Pharmacy workflow tested where enabled
- [ ] Referral workflow tested where enabled
- [ ] Admission/ward workflows tested where enabled
- [ ] Cash/private-payer care tested without SHA availability

## Health financing

- [ ] Coverage verification tested
- [ ] Benefits tested
- [ ] Preauthorization tested
- [ ] Billing tested
- [ ] Payment confirmation tested
- [ ] Claim validation tested
- [ ] Claim submission tested with an authorised payer integration
- [ ] Payer callback tested
- [ ] Rejection/rework tested
- [ ] Reconciliation tested
- [ ] Duplicate/idempotent operations tested

## Operational readiness

- [ ] Integration pending/retry/failed queues monitored
- [ ] Failed transaction recovery procedure tested
- [ ] Backup restore procedure tested
- [ ] Incident escalation contacts documented
- [ ] Deployment rollback procedure tested
- [ ] Request IDs are captured in operational logs
- [ ] Pilot support owner assigned

## Go-live decision

Pilot approval should require explicit sign-off from the relevant clinical, security/privacy, infrastructure, facility, and business/payer owners. Passing this checklist does not by itself establish statutory approval to operate as a national health financing system.
