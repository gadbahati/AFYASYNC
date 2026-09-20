# AfyaSync Beast Roadmap

**Positioning:** Facility operating system + multi-payer + patient portal — not a SHA clone.  
**Standalone first.** Cash always works. SHA is integrated, not the only path.  
**Developer:** BAHATI GAD WANGWE

---

## Shipped (Phases 1–9)

| Phase | Focus |
|-------|--------|
| 1–5 | Core HMIS, auth, clinical, billing, security hardening |
| 6 | Treat Abroad case machine |
| 7 | Notifications abstraction (SMS/email) |
| 8 | Claims UX / rejection workbench |
| 9 | Production migrations (`0071`/`0072`), `/ready` schema gate, deploy |

**Differentiating capabilities live:**

- Patient self-registration (Afya ID) + portal  
- Sensitive disease disclosure with digital consent  
- Bidirectional appointment requests + messaging  
- Treat Abroad procedures seed + case workflow  
- Claims preflight + production sandbox block  

---

## Phase 10 — Pilot / go-live gate (CURRENT)

**Docs:**

- `docs/PHASE10_PILOT_GOLIVE_GATE.md`  
- `docs/PHASE10_UAT_SCRIPT.md`  
- `docs/PHASE10_INCIDENT_RUNBOOK.md`  

**Exit:** UAT-01…10 pass, restore drill, sign-off → unlock Phase 11.

---

## Next beast phases (after gate)

| Phase | Title |
|-------|--------|
| 11 | SHA rejection prevention engine (risk score + KES at risk) |
| 12 | Consent-aware continuity card / QR wallet |
| 13 | Template-only safe patient messaging |
| 14 | USSD + low-bandwidth access |
| 15 | Treat Abroad return-home package |
| 16 | County/national care-gap intelligence (aggregates) |
| 17 | Multi-payer truth + out-of-pocket estimate |
| 18 | Prescribe-time allergy & med safety |
| 19 | Appointment fairness & capacity |
| 20 | Public trust layer |

---

## Non-negotiables every phase

1. No dummy credentials or fake clinician UUIDs  
2. Consent rules never bypassed  
3. Standalone care if SHA is offline  
4. Three-stakeholder benefit (individual, hospital, government)  
5. Harden before moving on  

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
