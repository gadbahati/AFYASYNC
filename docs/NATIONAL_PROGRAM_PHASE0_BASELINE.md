# AFYASYNC NATIONAL REPLACEMENT PROGRAM — PHASE 0 BASELINE

**Status:** COMPLETE (baseline gate)  
**Date:** 2026-09-22  
**Developer:** BAHATI GAD WANGWE  
**Strategic posture:** Not “feature-race SHA.” Build a **certifiable, interoperable national health operating & financing platform** that covers required functions around SHA, integrates with Kenya’s digital-health architecture (DHA / HIE / FHIR), and delivers an integrated experience for citizens, hospitals, clinicians, payers, and government.

**Repo scale (main, audited):**

| Layer | Count |
|-------|------:|
| Backend Python modules under `backend/app/` | ~305 files |
| Named domain packages | ~50 |
| SQLAlchemy tables (`__tablename__`) | **102** |
| API routers | **56** |
| Route decorators (approx.) | **~256** |
| Alembic migrations | **96** (through `0077_department_capacity`) |
| Backend tests | **67** |
| Frontend pages | **57** |
| Docs | **45** |

---

## 1. Architecture map (current)

```text
                         AFYASYNC (today)
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
   PATIENT / CITIZEN      FACILITY / CLINICAL      NATIONAL / GOV
   portal, USSD,          encounters → labs →       care-gap, capacity,
   continuity card,       pharmacy → billing →      referrals, supply,
   consent, booking       claims, wards, theatre    identity, reports
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                    IDENTITY (persons, Afya ID)
                    COVERAGE / PAYERS / BENEFITS
                    PREAUTH + CLAIMS + BILLING
                    INTEROP (partial FHIR export)
                    AUDIT + RBAC + PUBLIC TRUST
```

**Stack (as implemented):** FastAPI + SQLAlchemy + Alembic + JWT multi-role auth + React/TS frontend.

**Positioning already in code:** standalone-first (cash path), SHA as integrated payer path, not sole OS — consistent with national direction that SHA sits inside a wider digital-health ecosystem.

---

## 2. Capability catalogue vs repository

Legend: **E** = existing usable foundation · **I** = incomplete / thin · **M** = missing · **D** = duplicated risk · **H** = needs hardening before national claim

| Capability domain | Status | Repo anchors | Gap notes |
|-------------------|--------|--------------|-----------|
| Citizen portal | **E/I** | `portal/`, patient auth, booking, messages, consents, coverage views | Missing full timeline, wallet, “who accessed me”, grievances, charge explain |
| Identity / person registry | **E/I** | `patients/`, Afya identities, national identity routes | Missing household, dependants, deceased handling, confidence engine, employer links |
| Membership / contributions | **I/M** | coverage membership numbers | No contribution ledger, transfers, employer membership OS |
| Coverage | **E** | `coverage/` (19 files), adjudication, OOP estimate | Multi-payer truth exists; national benefit package versioning incomplete |
| Benefits | **E/I** | `benefits/`, benefit rules, packages UI | Limits/utilisation/family benefits incomplete |
| Facilities | **E** | `facilities/`, registry, KMHFR sync hooks | Certification onboarding pipeline incomplete |
| Practitioners / workforce | **I** | `rbac/` staff, roles | Licence, specialty, shift, digital twin missing |
| Clinical core | **E** | encounters, consultations, vitals, diagnoses, care plans, allergies | End-to-end orphan prevention needs systematic E2E |
| Appointments / queues | **E** | appointments, capacity, queue | Fairness/capacity added; full national scheduling thin |
| Laboratory | **E/I** | `laboratory/` order→sample→result | QC, TAT intelligence incomplete |
| Radiology | **E/I** | `radiology/` | Reporting depth incomplete |
| Pharmacy / stock | **E/I** | prescriptions, inventory, safety engine | Procurement, national shortage prediction incomplete |
| Admissions / wards | **E** | admissions, beds, movement | ICU specialty depth incomplete |
| Theatre | **E/I** | theatre bookings/procedures | Full peri-op OS incomplete |
| Emergency | **I** | triage/visits | **No** dispatch/ambulance/EMS FHIR handover chain |
| Referrals / capacity | **E/I** | referrals, national_capacity, national_referrals | Network search by specialty/beds/wait incomplete |
| Claims | **E/I** | claims lifecycle, preflight, risk | Full CMO-grade adjudication/appeals/payment stack incomplete |
| Preauthorisation | **E/I** | preauthorizations + SHA eligibility hooks | Real-time SHA EDI parity incomplete |
| Billing / payments | **E/I** | charges, invoices, payments | Bank settlement, double-entry tower incomplete |
| Reconciliation | **I** | claims reconcile permission | Full payment↔claim↔bank incomplete |
| Fraud / integrity | **I** | fraud radar signals (insight), claim risk | Integrity graph missing |
| Complaints / appeals | **M** | — | Patient protection suite missing |
| Interoperability / FHIR | **I** | interoperability routers, contract tests | Kenya Core full resource set incomplete; Conformance Lab missing |
| Public health programmes | **I** | maternity, child_health, infection_control | Oncology/mental health/population engines missing |
| Government intelligence | **E/I** | care_gap, reports, national command UI | Why/What-if engines missing |
| Supply chain | **I** | national_supply | Full supplier→patient chain incomplete |
| Security SOC | **I** | middleware, privacy, audit | MFA, threat ops, key mgmt incomplete |
| Offline / resilience | **M** | `offline/` empty package only | **Critical national gap** |
| Disaster recovery | **I** | docs/runbooks | Proven restore drills not productized |
| AI | **M** | — | Correctly deferred until evidence layer exists |
| DHA certification room | **M** | trust public APIs, privacy docs | Formal evidence matrix missing |
| Developer portal / sandbox | **I** | OpenAPI via FastAPI | SDK/certification portal missing |

---

## 3. Database map (summary)

**~102 tables** spanning identity, clinical, diagnostics, pharmacy, wards, claims, coverage, portal, consent, treat-abroad, USSD, continuity, capacity, audit, RBAC.

**Strengths:** clinical + claims + coverage + portal tables are real, migrated, and used by services.

**Gaps for national programme:**
- No household / dependant tables
- No contribution / membership ledger
- No grievance / appeal case tables
- No offline event / sync queue tables
- No tariff rule version store (rules partly in benefit tables, not full rules engine)
- No integrity-graph edge store
- No payment instruction / bank settlement tables at CMO depth
- `nutrition` duplicates `diet_orders` naming risk (**D**)

---

## 4. API inventory (summary)

| Area | Prefix examples | Maturity |
|------|-----------------|----------|
| Auth (staff + patient) | `/api/v1/auth`, `/api/v1/auth/patient` | **E/H** |
| Patients / clinical | `/api/v1/patients`, encounters, clinical | **E/H** |
| Coverage / payers | `/api/v1/coverage`, SHA, payer-network | **E/I** |
| Pharmacy + safety | `/api/v1/pharmacy` | **E/H** |
| Claims + preflight | `/api/v1/claims` | **E/I** |
| Portal + facility booking | `/api/v1/portal`, facility messages | **E/I** |
| National | care-gaps, capacity, referrals, supply, identity | **I** |
| Public trust | `/api/v1/public/*` | **E** (no PHI) |
| Interop | FHIR-ish allergy/patient exports | **I** |
| USSD | `/api/v1/ussd`, lite | **E/I** |

**~256** route decorators across **56** routers — large surface; national scale needs rate limits, bulk APIs, and conformance tests per resource.

---

## 5. Permission matrix (summary)

**~69** named permission-style constants observed (e.g. `claims.submit`, `pharmacy.prescription.create`, `clinical.allergy.write`, `reports.national.read`).

**Strengths:** facility-scoped staff permissions; patient routes separated.

**Gaps:**
- No systematic patient-facing permission catalogue for “who accessed my record”
- National roles (MOH analyst, county, auditor, investigator) incomplete
- Maker-checker for payments / rule activation missing
- Privilege matrix not exported as a single machine-readable artefact for DHA evidence

---

## 6. Workflow inventory

| Workflow | Code path | E2E orphan risk |
|----------|-----------|-----------------|
| Register → encounter → consult → diagnose | patients, encounters, clinical | Medium — needs forced linkage tests |
| Lab order → sample → result | laboratory | Medium |
| Rx → allergy check → dispense → charge | pharmacy + billing | Medium–High |
| Appointment request → accept → capacity | portal + appointments | Lower after Phase 19 |
| Invoice → claim → preflight → submit | billing + claims | Medium |
| Treat abroad → return package | treat_abroad | Lower within scope |
| Continuity card issue → verify | continuity | Lower |
| Emergency → ambulance → claim | emergency only thin | **High / mostly missing** |
| Offline encounter → sync | offline empty | **Critical missing** |

---

## 7. Migration inventory

- **96** versions; latest chain includes beast portal/consent, continuity, USSD, return packages, **department_capacity (0077)**.
- **Hardening note:** production readiness endpoint lists required tables; must stay in lockstep with new national tables.
- **Debt:** some historical restore migrations (`0062_restore_runtime_clinical_tables`) signal past schema pain — document and freeze patterns.

---

## 8. Integration inventory

| Integration | Status |
|-------------|--------|
| SHA eligibility / EDI direction | Partial service + router; not full live parity |
| KMHFR / facility registry | Sync hooks present |
| DHIS2 contract tests | Present in tests |
| FHIR export (allergy, patient-ish) | Partial |
| SMS/email notifications | Abstracted; production providers config-dependent |
| HIE bidirectional | **Missing** |
| Kenya EMS FHIR IG | **Missing** |
| Payment rails / bank | **Missing** |

---

## 9. Technical debt register (top)

1. **`offline/` empty** — national continuity requirement unmet.  
2. **Claims engine** not full CMO lifecycle (appeals, payment instruction, historical rule reconstruct).  
3. **Identity** lacks confidence engine, household, deceased, assisted/offline registration.  
4. **FHIR Kenya Core** incomplete vs required resource set.  
5. **Nutrition vs dietetics** table/name overlap risk.  
6. **Consent router** showed **0** decorator matches in static scan — verify registration (possible dynamic routes or scan miss; treat as **H**).  
7. **Test coverage skewed** toward auth, patients, claims, interop security — thin on pharmacy E2E, wards, theatre, emergency.  
8. **AI absent** (correct); do not add until evidence + security gates exist.  
9. **Certification evidence** not assembled as DHA “certification room.”  
10. **Performance** — no documented load-test baselines for national concurrency.

---

## 10. Security gap register (top)

| Gap | Severity | Notes |
|-----|----------|-------|
| MFA / hardware-backed staff auth | High | Password+JWT dominant |
| Secrets / key management productization | High | Env-based; needs KMS story for national |
| Offline encrypted store + signed events | High | Missing |
| Integrity graph / investigator workflow | Medium | Signals only |
| Patient “That wasn’t me” / access history | Medium | Missing product surface |
| Public metrics re-identification review process | Medium | Trust APIs OK; future transparency needs process |
| Pen-test / vulnerability pipeline as release gate | High | Not automated in-repo as mandatory gate |
| Ransomware / restore drill productization | High | Runbooks exist; not continuous proof |

---

## 11. Performance gap register (top)

| Gap | Notes |
|-----|-------|
| No published SLOs for booking / claim submit / eligibility | Need transaction-success SLOs, not only CPU |
| Bulk national APIs | Limited; county aggregates exist but not full bulk interchange |
| Queue / worker architecture | Partial via integrations; not universal async backbone |
| Read replicas / partitioning strategy | Not documented for national scale |
| Endurance tests | Not evidenced in-repo |

---

## 12. What NOT to build next (discipline)

Per programme rule: **no major greenfield feature without this baseline** — baseline is now written.

Still forbidden until their phase gate:
- Marketing “we replace SHA tomorrow”
- Autonomous clinical AI
- Unproven public person-level data
- Hardcoded national tariffs scattered in UI

---

## 13. Recommended implementation order (maps your Phases 1–40)

| Priority band | National phases | Why first |
|---------------|-----------------|-----------|
| **A — Foundation** | 1 Identity, 2 Coverage/Benefits, 13 Rules engine | Everything financial/clinical hangs on identity + versioned rules |
| **B — Hospital spine** | 4 Hospital OS E2E, 5 Safety, 6–7 Lab/Rx harden | Provider adoption |
| **C — Financing law** | 11 Claims beast, 12 Preauth, 14 Financial tower, 15 Integrity | SHA CMO-aligned functions |
| **D — Resilience** | 10 Offline, 30 DR | Network reality |
| **E — National mesh** | 8–9 Referral/EMS, 24 FHIR/HIE, 25 Terminology | DHA/HIE mandatory path |
| **F — Government** | 18–21 Graph, Command, Why, What-if | Policy credibility |
| **G — Assurance** | 33–37 Certification, pilot, evidence | Adoption package |
| **H — Scale & ops** | 27–29, 32, 38–40 | National operation |

**Immediate next engineering phase after Phase 0 gate:**  
**National Phase 1 — Afya Identity & Membership** (Identity Confidence Engine as beast feature), with hardening tests listed in the programme brief.

---

## 14. Phase 0 hardening gate — checklist

| Deliverable | Status |
|-------------|--------|
| Architecture map | **Done** (this doc §1) |
| Database map | **Done** (§3) |
| API inventory | **Done** (§4) |
| Permission matrix summary | **Done** (§5) |
| Workflow inventory | **Done** (§6) |
| Migration inventory | **Done** (§7) |
| Integration inventory | **Done** (§8) |
| Technical debt register | **Done** (§9) |
| Security gap register | **Done** (§10) |
| Performance gap register | **Done** (§11) |
| Capability catalogue E/I/M/D/H | **Done** (§2) |

**Gate decision:** Phase 0 **PASSED**. Major feature work may proceed **only** under National Programme phase numbers with explicit hardening gates.

---

## 15. Strategic reminder (non-negotiable)

Do **not** sell AfyaSync as “destroy SHA.”  
Build until evidence supports:

> This platform can perform required functions, integrates with Kenya’s digital-health architecture, satisfies certification requirements, protects citizens, serves providers, provides financial accountability, and has independently demonstrated operational performance.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
