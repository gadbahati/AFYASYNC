# Phase 10 — UAT script (hardened, no dummies)

**Developer:** BAHATI GAD WANGWE  
**Use with:** `docs/PHASE10_PILOT_GOLIVE_GATE.md`

Record: date, tester name, environment URL, API URL, pass/fail, notes, request IDs on failure.

---

## Preconditions

1. Production or pilot environment (not a laptop-only demo with fake JWT).  
2. `alembic upgrade head` applied (through **0072**).  
3. At least one **ACTIVE** facility and one **ACTIVE** staff user with facility membership.  
4. Frontend `VITE_API_BASE_URL` points at this API.  
5. No temporary test patient credentials in the UI.

---

## UAT-01 — Facility entry

1. Open `/login` → choose **Facility**.  
2. Sign in with real staff username/password.  
3. Select facility if prompted.  
4. Land on dashboard; facility name visible.  

**Pass:** Authenticated facility workspace.  
**Fail:** Invalid credentials message only (no stack traces, no user enumeration extras).

---

## UAT-02 — Patient self-registration

1. Open `/login` → **Patient** → **Create account**.  
2. Choose a **new** Afya ID (e.g. `AFYA-PILOT-…`), first/last name, password ≥ 8 chars.  
3. Optional phone/email.  
4. Submit → redirect `/portal`.  
5. Profile shows name + Afya ID.  

**Pass:** Account works; second register with same Afya ID is rejected.  
**Fail:** Any pre-filled test ID/password on the form.

---

## UAT-03 — Appointment request closed loop

1. As patient: `/portal/book` → select facility → reason ≥ 5 chars → send.  
2. As facility staff: open appointment requests / messages area that lists **PENDING** requests.  
3. Respond **ACCEPTED** (with offered time) or **DECLINED** with note.  
4. As patient: request list shows new status + notes/time.  

**Pass:** Both sides see the same outcome without phone workarounds.

---

## UAT-04 — Messaging round-trip

1. Patient sends message to facility.  
2. Facility inbox shows thread; staff replies.  
3. Patient sees reply.  

**Pass:** Ordered history; no cross-patient leakage.

---

## UAT-05 — Clinical path (minimum)

1. Staff registers or opens a patient.  
2. Start encounter; record vitals or consultation if UI allows.  
3. Add diagnosis.  
4. If sensitive category prompted: capture consent **with on-screen agreement** or mark facility-only.  

**Pass:** Data persists; patient portal consents list updates when consent exists.

---

## UAT-06 — Standalone / cash path

1. With SHA connector unavailable or unused, complete registration + encounter + invoice path for **cash**.  
2. Confirm UI does not hard-block care on SHA failure.  

**Pass:** Care and billing continue offline from SHA.

---

## UAT-07 — Claims discipline

1. Create invoice from closed encounter (or existing invoice).  
2. Run **preflight**.  
3. Create/validate claim as allowed.  
4. Attempt **sandbox reject** in production → must **fail/block**.  

**Pass:** Preflight returns actionable output; sandbox blocked in production.

---

## UAT-08 — Treat Abroad

1. Staff → Treat Abroad page.  
2. Procedures dropdown is **not empty** (seed from 0072 or on-demand seed).  
3. Create case as DRAFT with real patient + procedure + clinical summary ≥ 20 chars.  
4. Advance status once (e.g. DRAFT → SUBMITTED) if permitted.  

**Pass:** No dummy `referring_clinician_id` in network payload; server assigns staff.

---

## UAT-09 — Password reset hygiene

1. Request reset for existing patient channel (phone/email on file).  
2. Request reset for **unknown** identifier.  
3. Confirm responses do not clearly reveal which accounts exist (generic success messaging).  
4. Confirm code expires / single-use after confirm (if code captured from console provider in pilot).  

**Pass:** Safe messaging; codes not stored plaintext in DB.

---

## UAT-10 — Fail closed

1. Patient token → try open `/` facility routes → redirected to portal.  
2. Staff of Facility A → cannot load Facility B patient by ID (403/404).  
3. Expired/invalid JWT → login required.  

**Pass:** No silent privilege escalation.

---

## Evidence pack (attach to pilot file)

- Screenshots or short notes per UAT ID  
- `GET /ready` JSON (date/time)  
- `alembic current` output  
- Backup restore test date  
- List of known defects (P1/P2/P3)  

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
