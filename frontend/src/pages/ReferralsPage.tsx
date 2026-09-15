import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { FacilityOption, Patient, Referral } from "../api/types";
import { getAccessToken } from "../auth/storage";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function loadFacilityDirectory(): Promise<FacilityOption[]> {
  const response = await fetch(`${API_BASE}/api/v1/facilities/directory`, { headers: { Authorization: `Bearer ${getAccessToken() || ""}` } });
  if (!response.ok) throw new Error("FACILITY_DIRECTORY_FAILED");
  return response.json() as Promise<FacilityOption[]>;
}

export function ReferralsPage() {
  const [params] = useSearchParams();
  const encounterId = params.get("encounterId") || "";
  const [rows, setRows] = useState<Referral[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [facilities, setFacilities] = useState<FacilityOption[]>([]);
  const [role, setRole] = useState<"all" | "source" | "destination">("all");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ encounter_id: encounterId, destination_facility_id: "", reason: "", priority: "ROUTINE", clinical_summary: "" });

  async function load() {
    setLoading(true); setError(null);
    try {
      const [referrals, people, directory] = await Promise.all([api.listReferrals(role), api.listPatients(200, 0), loadFacilityDirectory()]);
      setRows(referrals.items); setPatients(people.items); setFacilities(directory);
    } catch (err) { setError(err instanceof ApiError ? err.code : err instanceof Error ? err.message : "LOAD_FAILED"); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, [role]);
  useEffect(() => { if (encounterId) setForm((f) => ({ ...f, encounter_id: encounterId })); }, [encounterId]);

  async function decide(id: string, status: "ACCEPTED" | "DECLINED") {
    setBusy(true); setError(null);
    try { const updated = await api.updateReferralStatus(id, status); setRows((current) => current.map((item) => item.id === id ? updated : item)); setMessage(`Referral ${status.toLowerCase()}`); }
    catch (err) { setError(err instanceof ApiError ? err.code : "UPDATE_FAILED"); }
    finally { setBusy(false); }
  }
  async function onCreate(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError(null); setMessage(null);
    try { await api.createReferral({ encounter_id: form.encounter_id.trim(), destination_facility_id: form.destination_facility_id, reason: form.reason.trim(), priority: form.priority, clinical_summary: form.clinical_summary.trim() || null }); setMessage("Referral created and sent to the receiving facility."); setForm({ encounter_id: "", destination_facility_id: "", reason: "", priority: "ROUTINE", clinical_summary: "" }); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.code : "CREATE_FAILED"); }
    finally { setBusy(false); }
  }
  const patientName = (id: string) => { const p = patients.find((x) => x.id === id); return p ? [p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ") : id; };
  const facilityName = (id: string) => facilities.find((f) => f.facility_id === id)?.facility_name || id;

  return <section className="page-stack">
    <header className="page-heading"><div><p className="eyebrow">Continuity & transfer</p><h1>Referrals & transfers</h1><p className="muted">Select the receiving hospital by name. The same live facility directory used across AfyaSync is used here, so staff do not have to enter facility UUIDs.</p></div><div className="form-actions"><button type="button" className={role === "all" ? "button" : "button secondary"} onClick={() => setRole("all")}>All</button><button type="button" className={role === "source" ? "button" : "button secondary"} onClick={() => setRole("source")}>Sent</button><button type="button" className={role === "destination" ? "button" : "button secondary"} onClick={() => setRole("destination")}>Receiving</button></div></header>
    {error && <div className="error">{error}</div>}{message && <div className="success-box">{message}</div>}
    <article className="card"><h2>Create referral</h2><p className="muted">When opened from a patient journey the encounter is carried automatically. Choose the receiving facility by name.</p><form className="form-grid" onSubmit={onCreate}><label className="full">Encounter ID<input required value={form.encounter_id} onChange={(e) => setForm({ ...form, encounter_id: e.target.value })} placeholder="Linked from patient journey" /></label><label className="full">Receiving facility<select required value={form.destination_facility_id} onChange={(e) => setForm({ ...form, destination_facility_id: e.target.value })}><option value="">Select receiving hospital</option>{facilities.map((facility) => <option key={facility.facility_id} value={facility.facility_id}>{facility.facility_name}</option>)}</select></label><label>Priority<select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}><option value="ROUTINE">Routine</option><option value="URGENT">Urgent</option><option value="EMERGENCY">Emergency</option></select></label><label>Reason<input required value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></label><label className="full">Clinical summary<textarea value={form.clinical_summary} onChange={(e) => setForm({ ...form, clinical_summary: e.target.value })} /></label><div className="full actions"><button type="submit" disabled={busy || facilities.length === 0}>{busy ? "Submitting…" : "Create referral"}</button></div></form></article>
    {loading ? <p>Loading referrals…</p> : <div className="table-wrap"><table><thead><tr><th>Referral</th><th>Patient</th><th>From</th><th>To</th><th>Reason</th><th>Status</th><th>Receiving action</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{row.referral_id}</td><td><Link to={`/patients/${row.patient_id}/journey`}><strong>{patientName(row.patient_id)}</strong></Link></td><td>{facilityName(row.source_facility_id)}</td><td>{facilityName(row.destination_facility_id)}</td><td>{row.reason}</td><td><span className="status-pill">{row.status}</span></td><td>{row.status === "SENT" || row.status === "CREATED" ? <div className="form-actions"><button type="button" disabled={busy} onClick={() => void decide(row.id, "ACCEPTED")}>Accept & receive</button><button type="button" className="button secondary" disabled={busy} onClick={() => void decide(row.id, "DECLINED")}>Decline</button></div> : <span className="muted">No action</span>}</td></tr>)}{rows.length === 0 && <tr><td colSpan={7} className="muted">No referrals for this facility.</td></tr>}</tbody></table></div>}
  </section>;
}
