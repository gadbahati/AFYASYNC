import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Patient } from "../api/types";
import { getAccessToken } from "../auth/storage";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

type Pregnancy = { id: string; patient_id: string; gravida: number | null; para: number | null; lmp: string | null; estimated_due_date: string | null; gestational_age_weeks: number | null; risk_level: string; status: string };
type ChildRecord = { id: string; patient_id: string; mother_id: string | null; birth_date: string | null; birth_weight: string | null; status: string };

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", Authorization: `Bearer ${getAccessToken() || ""}`, ...(init.headers || {}) } });
  if (!response.ok) {
    let detail = "REQUEST_FAILED";
    try { const body = await response.json(); detail = typeof body.detail === "string" ? body.detail : detail; } catch { /* preserve stable error */ }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

const nameOf = (people: Patient[], id: string) => { const p = people.find((item) => item.id === id); return p ? [p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ") : id; };

export function MCHPage() {
  const [tab, setTab] = useState<"maternal" | "child">("maternal");
  const [patients, setPatients] = useState<Patient[]>([]);
  const [pregnancies, setPregnancies] = useState<Pregnancy[]>([]);
  const [children, setChildren] = useState<ChildRecord[]>([]);
  const [selectedPregnancy, setSelectedPregnancy] = useState("");
  const [selectedChild, setSelectedChild] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pregnancyForm, setPregnancyForm] = useState({ patient_id: "", gravida: "", para: "", lmp: "", estimated_due_date: "", gestational_age_weeks: "", risk_level: "ROUTINE" });
  const [ancForm, setAncForm] = useState({ gestational_age_weeks: "", blood_pressure: "", weight: "", fetal_heart_rate: "", findings: "", plan: "" });
  const [childForm, setChildForm] = useState({ patient_id: "", mother_id: "", birth_date: "", birth_weight: "", notes: "" });
  const [growthForm, setGrowthForm] = useState({ age_months: "", weight: "", height: "", head_circumference: "", assessment: "" });
  const [immunisationForm, setImmunisationForm] = useState({ vaccine: "", dose: "", next_due_at: "", batch_number: "", notes: "" });

  async function load() {
    setError(null);
    try {
      const [people, maternity, child] = await Promise.all([api.listPatients(200, 0), requestJson<Pregnancy[]>("/api/v1/maternity/pregnancies"), requestJson<ChildRecord[]>("/api/v1/child-health/records")]);
      setPatients(people.items); setPregnancies(maternity); setChildren(child);
    } catch (err) { setError(err instanceof ApiError ? err.code : "MCH_LOAD_FAILED"); }
  }
  useEffect(() => { void load(); }, []);

  const women = useMemo(() => patients.filter((p) => p.sex === "FEMALE"), [patients]);
  const activePregnancies = pregnancies.filter((p) => p.status === "ACTIVE");
  const selectedPatient = pregnancyForm.patient_id ? nameOf(patients, pregnancyForm.patient_id) : "No patient selected";
  const selectedChildName = selectedChild ? nameOf(patients, children.find((c) => c.id === selectedChild)?.patient_id || "") : "No child selected";

  async function submitPregnancy(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null); setMessage(null);
    try {
      const created = await requestJson<Pregnancy>("/api/v1/maternity/pregnancies", { method: "POST", body: JSON.stringify({ patient_id: pregnancyForm.patient_id, gravida: pregnancyForm.gravida ? Number(pregnancyForm.gravida) : null, para: pregnancyForm.para ? Number(pregnancyForm.para) : null, lmp: pregnancyForm.lmp || null, estimated_due_date: pregnancyForm.estimated_due_date || null, gestational_age_weeks: pregnancyForm.gestational_age_weeks ? Number(pregnancyForm.gestational_age_weeks) : null, risk_level: pregnancyForm.risk_level }) });
      setPregnancies((rows) => [created, ...rows]); setSelectedPregnancy(created.id); setMessage(`Pregnancy registered for ${selectedPatient}.`);
    } catch (err) { setError(err instanceof ApiError ? err.code : "PREGNANCY_CREATE_FAILED"); }
    finally { setBusy(false); }
  }

  async function submitAnc(event: FormEvent) {
    event.preventDefault(); if (!selectedPregnancy) return; setBusy(true); setError(null); setMessage(null);
    try { await requestJson(`/api/v1/maternity/pregnancies/${selectedPregnancy}/visits`, { method: "POST", body: JSON.stringify({ gestational_age_weeks: ancForm.gestational_age_weeks ? Number(ancForm.gestational_age_weeks) : null, blood_pressure: ancForm.blood_pressure || null, weight: ancForm.weight || null, fetal_heart_rate: ancForm.fetal_heart_rate || null, findings: ancForm.findings || null, plan: ancForm.plan || null }) }); setMessage("Antenatal visit recorded successfully."); setAncForm({ gestational_age_weeks: "", blood_pressure: "", weight: "", fetal_heart_rate: "", findings: "", plan: "" }); }
    catch (err) { setError(err instanceof ApiError ? err.code : "ANC_VISIT_FAILED"); }
    finally { setBusy(false); }
  }

  async function submitChild(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null); setMessage(null);
    try { const created = await requestJson<ChildRecord>("/api/v1/child-health/records", { method: "POST", body: JSON.stringify({ patient_id: childForm.patient_id, mother_id: childForm.mother_id || null, birth_date: childForm.birth_date || null, birth_weight: childForm.birth_weight || null, notes: childForm.notes || null }) }); setChildren((rows) => [created, ...rows]); setSelectedChild(created.id); setMessage(`Child health record registered for ${nameOf(patients, created.patient_id)}.`); }
    catch (err) { setError(err instanceof ApiError ? err.code : "CHILD_REGISTER_FAILED"); }
    finally { setBusy(false); }
  }

  async function submitGrowth(event: FormEvent) {
    event.preventDefault(); if (!selectedChild) return; setBusy(true); setError(null); setMessage(null);
    try { await requestJson(`/api/v1/child-health/records/${selectedChild}/growth`, { method: "POST", body: JSON.stringify({ age_months: growthForm.age_months ? Number(growthForm.age_months) : null, weight: growthForm.weight || null, height: growthForm.height || null, head_circumference: growthForm.head_circumference || null, assessment: growthForm.assessment || null }) }); setMessage("Growth observation recorded."); }
    catch (err) { setError(err instanceof ApiError ? err.code : "GROWTH_RECORD_FAILED"); }
    finally { setBusy(false); }
  }

  async function submitImmunisation(event: FormEvent) {
    event.preventDefault(); if (!selectedChild) return; setBusy(true); setError(null); setMessage(null);
    try { await requestJson(`/api/v1/child-health/records/${selectedChild}/immunisations`, { method: "POST", body: JSON.stringify({ vaccine: immunisationForm.vaccine, dose: immunisationForm.dose, next_due_at: immunisationForm.next_due_at || null, batch_number: immunisationForm.batch_number || null, notes: immunisationForm.notes || null }) }); setMessage("Immunisation recorded."); }
    catch (err) { setError(err instanceof ApiError ? err.code : "IMMUNISATION_FAILED"); }
    finally { setBusy(false); }
  }

  return <section className="page-stack">
    <header className="page-heading"><div><p className="eyebrow">Maternal & Child Health</p><h1>MCH services</h1><p className="muted">MCH means <strong>Maternal and Child Health</strong>. This workspace covers pregnancy registration, antenatal care, child health, growth monitoring and immunisation using the same patient and facility records as the rest of AfyaSync.</p></div></header>
    {error && <div className="error">{error}</div>}{message && <div className="success-box">{message}</div>}
    <div className="form-actions"><button className={tab === "maternal" ? "button" : "button secondary"} type="button" onClick={() => setTab("maternal")}>Maternal / ANC</button><button className={tab === "child" ? "button" : "button secondary"} type="button" onClick={() => setTab("child")}>Child health</button></div>
    {tab === "maternal" ? <>
      <article className="card"><h2>Register pregnancy</h2><form className="form-grid" onSubmit={submitPregnancy}><label className="full">Mother / patient<select required value={pregnancyForm.patient_id} onChange={(e) => setPregnancyForm({ ...pregnancyForm, patient_id: e.target.value })}><option value="">Select patient</option>{women.map((p) => <option key={p.id} value={p.id}>{[p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ")}</option>)}</select></label><label>Gravida<input type="number" min="0" value={pregnancyForm.gravida} onChange={(e) => setPregnancyForm({ ...pregnancyForm, gravida: e.target.value })} /></label><label>Para<input type="number" min="0" value={pregnancyForm.para} onChange={(e) => setPregnancyForm({ ...pregnancyForm, para: e.target.value })} /></label><label>LMP<input type="date" value={pregnancyForm.lmp} onChange={(e) => setPregnancyForm({ ...pregnancyForm, lmp: e.target.value })} /></label><label>Estimated due date<input type="date" value={pregnancyForm.estimated_due_date} onChange={(e) => setPregnancyForm({ ...pregnancyForm, estimated_due_date: e.target.value })} /></label><label>Gestational age (weeks)<input type="number" min="0" max="45" value={pregnancyForm.gestational_age_weeks} onChange={(e) => setPregnancyForm({ ...pregnancyForm, gestational_age_weeks: e.target.value })} /></label><label>Risk<select value={pregnancyForm.risk_level} onChange={(e) => setPregnancyForm({ ...pregnancyForm, risk_level: e.target.value })}><option>ROUTINE</option><option>HIGH</option><option>EMERGENCY</option></select></label><div className="full actions"><button type="submit" disabled={busy}>{busy ? "Saving…" : "Register pregnancy"}</button></div></form></article>
      <article className="card"><h2>Record antenatal visit</h2><label>Pregnancy<select value={selectedPregnancy} onChange={(e) => setSelectedPregnancy(e.target.value)}><option value="">Select active pregnancy</option>{activePregnancies.map((p) => <option key={p.id} value={p.id}>{nameOf(patients, p.patient_id)} — {p.risk_level} — {p.gestational_age_weeks ?? "—"} weeks</option>)}</select></label><form className="form-grid" onSubmit={submitAnc}><label>Gestational age<input type="number" min="0" max="45" value={ancForm.gestational_age_weeks} onChange={(e) => setAncForm({ ...ancForm, gestational_age_weeks: e.target.value })} /></label><label>Blood pressure<input value={ancForm.blood_pressure} onChange={(e) => setAncForm({ ...ancForm, blood_pressure: e.target.value })} placeholder="e.g. 120/80" /></label><label>Weight<input value={ancForm.weight} onChange={(e) => setAncForm({ ...ancForm, weight: e.target.value })} /></label><label>Fetal heart rate<input value={ancForm.fetal_heart_rate} onChange={(e) => setAncForm({ ...ancForm, fetal_heart_rate: e.target.value })} /></label><label className="full">Findings<textarea value={ancForm.findings} onChange={(e) => setAncForm({ ...ancForm, findings: e.target.value })} /></label><label className="full">Plan<textarea value={ancForm.plan} onChange={(e) => setAncForm({ ...ancForm, plan: e.target.value })} /></label><div className="full actions"><button type="submit" disabled={busy || !selectedPregnancy}>{busy ? "Saving…" : "Record ANC visit"}</button></div></form></article>
    </> : <>
      <article className="card"><h2>Register child health record</h2><form className="form-grid" onSubmit={submitChild}><label className="full">Child / patient<select required value={childForm.patient_id} onChange={(e) => setChildForm({ ...childForm, patient_id: e.target.value })}><option value="">Select child patient</option>{patients.map((p) => <option key={p.id} value={p.id}>{[p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ")}</option>)}</select></label><label className="full">Mother (optional)<select value={childForm.mother_id} onChange={(e) => setChildForm({ ...childForm, mother_id: e.target.value })}><option value="">Select mother</option>{women.map((p) => <option key={p.id} value={p.id}>{[p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ")}</option>)}</select></label><label>Birth date<input type="date" value={childForm.birth_date} onChange={(e) => setChildForm({ ...childForm, birth_date: e.target.value })} /></label><label>Birth weight<input value={childForm.birth_weight} onChange={(e) => setChildForm({ ...childForm, birth_weight: e.target.value })} placeholder="e.g. 3.2 kg" /></label><label className="full">Notes<textarea value={childForm.notes} onChange={(e) => setChildForm({ ...childForm, notes: e.target.value })} /></label><div className="full actions"><button type="submit" disabled={busy}>{busy ? "Saving…" : "Register child"}</button></div></form></article>
      <article className="card"><h2>Growth & immunisation</h2><label>Child record<select value={selectedChild} onChange={(e) => setSelectedChild(e.target.value)}><option value="">Select child</option>{children.map((c) => <option key={c.id} value={c.id}>{nameOf(patients, c.patient_id)} — {c.birth_date || "birth date not recorded"}</option>)}</select></label><p className="muted">Selected: {selectedChildName}</p><form className="form-grid" onSubmit={submitGrowth}><label>Age (months)<input type="number" min="0" max="216" value={growthForm.age_months} onChange={(e) => setGrowthForm({ ...growthForm, age_months: e.target.value })} /></label><label>Weight<input value={growthForm.weight} onChange={(e) => setGrowthForm({ ...growthForm, weight: e.target.value })} /></label><label>Height<input value={growthForm.height} onChange={(e) => setGrowthForm({ ...growthForm, height: e.target.value })} /></label><label>Head circumference<input value={growthForm.head_circumference} onChange={(e) => setGrowthForm({ ...growthForm, head_circumference: e.target.value })} /></label><label className="full">Assessment<textarea value={growthForm.assessment} onChange={(e) => setGrowthForm({ ...growthForm, assessment: e.target.value })} /></label><div className="full actions"><button type="submit" disabled={busy || !selectedChild}>Record growth</button></div></form><hr /><form className="form-grid" onSubmit={submitImmunisation}><label>Vaccine<input required value={immunisationForm.vaccine} onChange={(e) => setImmunisationForm({ ...immunisationForm, vaccine: e.target.value })} placeholder="e.g. BCG" /></label><label>Dose<input required value={immunisationForm.dose} onChange={(e) => setImmunisationForm({ ...immunisationForm, dose: e.target.value })} placeholder="e.g. Birth dose" /></label><label>Next due<input type="datetime-local" value={immunisationForm.next_due_at} onChange={(e) => setImmunisationForm({ ...immunisationForm, next_due_at: e.target.value })} /></label><label>Batch number<input value={immunisationForm.batch_number} onChange={(e) => setImmunisationForm({ ...immunisationForm, batch_number: e.target.value })} /></label><label className="full">Notes<textarea value={immunisationForm.notes} onChange={(e) => setImmunisationForm({ ...immunisationForm, notes: e.target.value })} /></label><div className="full actions"><button type="submit" disabled={busy || !selectedChild}>Record immunisation</button></div></form></article>
    </>}
    <article className="card"><h2>Patient continuity</h2><p className="muted">MCH records are tied to the selected patient and current facility. Open the patient journey to see the wider clinical, referral, laboratory, pharmacy and billing history.</p>{patients.length > 0 && <Link className="button secondary" to="/patients">Open patient register</Link>}</article>
  </section>;
}
