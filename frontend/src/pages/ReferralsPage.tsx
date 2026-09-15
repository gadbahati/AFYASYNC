import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { FacilityOption, Patient, Referral, Transfer } from "../api/types";

export function ReferralsPage() {
  const [params] = useSearchParams();
  const encounterId = params.get("encounterId") || "";
  const [rows, setRows] = useState<Referral[]>([]);
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [facilities, setFacilities] = useState<FacilityOption[]>([]);
  const [role, setRole] = useState<"all" | "source" | "destination">("all");
  const [facilitySearch, setFacilitySearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ encounter_id: encounterId, destination_facility_id: "", reason: "", priority: "ROUTINE", clinical_summary: "" });

  async function loadFacilities(search = "") {
    try { setFacilities(await api.facilityDirectory(search)); }
    catch (err) { setError(err instanceof ApiError ? err.code : "FACILITY_DIRECTORY_FAILED"); }
  }
  async function load() {
    setLoading(true); setError(null);
    try {
      const [referrals, transferRows, people] = await Promise.all([api.listReferrals(role), api.listTransfers(role), api.listPatients(200, 0)]);
      setRows(referrals.items); setTransfers(transferRows.items); setPatients(people.items); await loadFacilities(facilitySearch);
    } catch (err) { setError(err instanceof ApiError ? err.code : err instanceof Error ? err.message : "LOAD_FAILED"); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, [role]);
  useEffect(() => { if (encounterId) setForm((f) => ({ ...f, encounter_id: encounterId })); }, [encounterId]);
  useEffect(() => { const timer = window.setTimeout(() => { void loadFacilities(facilitySearch); }, 250); return () => window.clearTimeout(timer); }, [facilitySearch]);

  async function decideReferral(id: string, status: "ACCEPTED" | "DECLINED") {
    setBusy(true); setError(null);
    try { await api.updateReferralStatus(id, status); setMessage(`Referral ${status === "ACCEPTED" ? "accepted by the receiving facility" : "declined"}.`); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.code : "UPDATE_FAILED"); }
    finally { setBusy(false); }
  }
  async function sendAcceptedReferralAsTransfer(referral: Referral) {
    setBusy(true); setError(null);
    try { await api.createTransfer({ encounter_id: referral.encounter_id, destination_facility_id: referral.destination_facility_id, referral_id: referral.id, reason: referral.reason, notes: referral.clinical_summary }); setMessage("Transfer request sent. The receiving facility must accept it before movement."); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.code : "TRANSFER_CREATE_FAILED"); }
    finally { setBusy(false); }
  }
  async function updateTransfer(id: string, status: "ACCEPTED" | "IN_TRANSIT" | "ARRIVED" | "CANCELLED") {
    setBusy(true); setError(null);
    try { await api.updateTransferStatus(id, status); setMessage(`Transfer status updated to ${status.replace("_", " ").toLowerCase()}.`); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.code : "TRANSFER_UPDATE_FAILED"); }
    finally { setBusy(false); }
  }
  async function onCreate(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError(null); setMessage(null);
    try {
      await api.createReferral({ encounter_id: form.encounter_id.trim(), destination_facility_id: form.destination_facility_id, reason: form.reason.trim(), priority: form.priority, clinical_summary: form.clinical_summary.trim() || null });
      setMessage("Referral sent. The receiving facility must accept it before a transfer request can be created.");
      setForm({ encounter_id: "", destination_facility_id: "", reason: "", priority: "ROUTINE", clinical_summary: "" });
      await load();
    } catch (err) { setError(err instanceof ApiError ? err.code : "CREATE_FAILED"); }
    finally { setBusy(false); }
  }
  const patientName = (id: string) => { const p = patients.find((x) => x.id === id); return p ? [p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ") : id; };
  const facilityName = (id: string) => facilities.find((f) => f.facility_id === id)?.facility_name || id;
  const selectedFacility = useMemo(() => facilities.find((f) => f.facility_id === form.destination_facility_id), [facilities, form.destination_facility_id]);

  return <section className="page-stack">
    <header className="page-heading"><div><p className="eyebrow">Continuity & transfer</p><h1>Referrals & transfers</h1><p className="muted">Search the same Kenya facility network used at entry. Send a referral, wait for acceptance, then create and track the physical transfer.</p></div><div className="form-actions"><button type="button" className={role === "all" ? "button" : "button secondary"} onClick={() => setRole("all")}>All</button><button type="button" className={role === "source" ? "button" : "button secondary"} onClick={() => setRole("source")}>Sent</button><button type="button" className={role === "destination" ? "button" : "button secondary"} onClick={() => setRole("destination")}>Receiving</button></div></header>
    {error && <div className="error">{error}</div>}{message && <div className="success-box">{message}</div>}
    <article className="card"><h2>Send patient referral</h2><p className="muted">The referral is sent to the selected facility. No patient movement is authorised by this action alone.</p><form className="form-grid" onSubmit={onCreate}><label className="full">Encounter ID<input required value={form.encounter_id} onChange={(e) => setForm({ ...form, encounter_id: e.target.value })} placeholder="Open this page from the patient journey to fill automatically" /></label><label className="full">Search receiving facility<input value={facilitySearch} onChange={(e) => setFacilitySearch(e.target.value)} placeholder="Search hospital, health centre, dispensary…" /></label><label className="full">Receiving facility<select required value={form.destination_facility_id} onChange={(e) => setForm({ ...form, destination_facility_id: e.target.value })}><option value="">Select receiving facility</option>{facilities.map((facility) => <option key={facility.facility_id} value={facility.facility_id}>{facility.facility_name}</option>)}</select>{selectedFacility && <span className="muted small">Selected: {selectedFacility.facility_name}</span>}</label><label>Priority<select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}><option value="ROUTINE">Routine</option><option value="URGENT">Urgent</option><option value="EMERGENCY">Emergency</option></select></label><label>Reason<input required value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></label><label className="full">Clinical summary<textarea value={form.clinical_summary} onChange={(e) => setForm({ ...form, clinical_summary: e.target.value })} /></label><div className="full actions"><button type="submit" disabled={busy || !form.destination_facility_id}>{busy ? "Sending…" : "Send referral"}</button></div></form></article>
    {loading ? <p>Loading referral network…</p> : <>
      <article className="card"><h2>Referral decisions</h2><div className="table-wrap"><table><thead><tr><th>Patient</th><th>From</th><th>To</th><th>Priority</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td><Link to={`/patients/${row.patient_id}/journey`}><strong>{patientName(row.patient_id)}</strong></Link></td><td>{facilityName(row.source_facility_id)}</td><td>{facilityName(row.destination_facility_id)}</td><td>{row.priority}</td><td><span className="status-pill">{row.status}</span></td><td>{(row.status === "SENT" || row.status === "CREATED") && role === "destination" ? <div className="form-actions"><button type="button" disabled={busy} onClick={() => void decideReferral(row.id, "ACCEPTED")}>Accept referral</button><button type="button" className="button secondary" disabled={busy} onClick={() => void decideReferral(row.id, "DECLINED")}>Decline</button></div> : role === "source" && row.status === "ACCEPTED" && !transfers.some((t) => t.referral_id === row.id) ? <button type="button" disabled={busy} onClick={() => void sendAcceptedReferralAsTransfer(row)}>Request transfer</button> : <span className="muted">{row.status === "ACCEPTED" ? "Accepted" : "Waiting"}</span>}</td></tr>)}{rows.length === 0 && <tr><td colSpan={6} className="muted">No referrals in this view.</td></tr>}</tbody></table></div></article>
      <article className="card"><h2>Transfer requests</h2><p className="muted">After referral acceptance, the transfer request is accepted by the receiving facility. The source facility then marks the patient in transit; the destination records arrival.</p><div className="table-wrap"><table><thead><tr><th>Transfer</th><th>Patient</th><th>From</th><th>To</th><th>Status</th><th>Action</th></tr></thead><tbody>{transfers.map((row) => <tr key={row.id}><td>{row.transfer_id}</td><td><Link to={`/patients/${row.patient_id}/journey`}>{patientName(row.patient_id)}</Link></td><td>{facilityName(row.source_facility_id)}</td><td>{facilityName(row.destination_facility_id)}</td><td><span className="status-pill">{row.status}</span></td><td>{role === "destination" && row.status === "REQUESTED" ? <button type="button" disabled={busy} onClick={() => void updateTransfer(row.id, "ACCEPTED")}>Accept transfer</button> : role === "source" && row.status === "ACCEPTED" ? <button type="button" disabled={busy} onClick={() => void updateTransfer(row.id, "IN_TRANSIT")}>Start transfer</button> : role === "destination" && row.status === "IN_TRANSIT" ? <button type="button" disabled={busy} onClick={() => void updateTransfer(row.id, "ARRIVED")}>Mark arrived</button> : <span className="muted">{row.status === "ARRIVED" ? "Patient arrived" : "Waiting"}</span>}</td></tr>)}{transfers.length === 0 && <tr><td colSpan={6} className="muted">No transfer requests in this view.</td></tr>}</tbody></table></div></article>
    </>}
  </section>;
}
