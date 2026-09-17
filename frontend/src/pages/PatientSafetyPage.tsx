import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";

type Allergy = { id: string; patient_id: string; facility_id: string; allergen: string; reaction: string | null; severity: string; status: string; onset_date: string | null; notes: string | null; created_at: string; updated_at: string };

const severityLabel = (value: string) => value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, c => c.toUpperCase());

export function PatientSafetyPage() {
  const { patientId } = useParams();
  const [items, setItems] = useState<Allergy[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ allergen: "", reaction: "", severity: "UNKNOWN", onset_date: "", notes: "" });

  const load = () => {
    if (!patientId) return;
    setLoading(true);
    setError(null);
    api.listPatientAllergies(patientId, true).then(setItems).catch((e) => setError(e instanceof ApiError ? e.code : "ALLERGIES_LOAD_FAILED")).finally(() => setLoading(false));
  };
  useEffect(load, [patientId]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!patientId || !form.allergen.trim()) return;
    setSaving(true); setError(null);
    try {
      await api.createPatientAllergy(patientId, { ...form, reaction: form.reaction || null, onset_date: form.onset_date || null, notes: form.notes || null });
      setForm({ allergen: "", reaction: "", severity: "UNKNOWN", onset_date: "", notes: "" });
      load();
    } catch (e) { setError(e instanceof ApiError ? e.code : "ALLERGY_CREATE_FAILED"); }
    finally { setSaving(false); }
  };

  const deactivate = async (item: Allergy) => {
    if (!patientId || item.status !== "ACTIVE") return;
    try { await api.updatePatientAllergy(patientId, item.id, { status: "INACTIVE" }); load(); }
    catch (e) { setError(e instanceof ApiError ? e.code : "ALLERGY_UPDATE_FAILED"); }
  };

  return <section className="page-stack">
    <header className="page-header"><div><Link to={`/patients/${patientId}`} className="muted">← Patient record</Link><h1>Clinical safety</h1><p className="muted">Allergies and adverse-reaction information for this patient.</p></div></header>
    {error && <div className="error" role="alert">Unable to complete request: {error}</div>}
    <div className="card" style={{ borderLeft: "4px solid currentColor" }}><strong>Medication safety</strong><p className="muted">Active allergies are checked by the medication safety API when medicines are reviewed. Severe and life-threatening matches require clinical review.</p></div>
    <section className="card"><div className="row-between"><div><h2>Recorded allergies</h2><p className="muted">{items.filter(x => x.status === "ACTIVE").length} active · {items.length} total recorded</p></div></div>
      {loading ? <p>Loading allergies…</p> : items.length === 0 ? <p className="muted">No allergies have been recorded.</p> : <div className="record-list">{items.map(item => <article className="record-row" key={item.id}><div><strong>{item.allergen}</strong><div className="muted">{item.reaction || "Reaction not recorded"} · Severity: {severityLabel(item.severity)}</div>{item.onset_date && <div className="muted small">Onset {item.onset_date}</div>}{item.notes && <div className="small">{item.notes}</div>}</div><div className="right"><span className="badge">{item.status}</span>{item.status === "ACTIVE" && <button type="button" className="button secondary" onClick={() => deactivate(item)}>Mark inactive</button>}</div></article>)}</div>}
    </section>
    <section className="card"><h2>Record allergy</h2><form onSubmit={submit} className="form-grid"><label>Allergen<input required value={form.allergen} onChange={e => setForm({ ...form, allergen: e.target.value })} placeholder="e.g. Penicillin" /></label><label>Reaction<input value={form.reaction} onChange={e => setForm({ ...form, reaction: e.target.value })} placeholder="e.g. Rash, anaphylaxis" /></label><label>Severity<select value={form.severity} onChange={e => setForm({ ...form, severity: e.target.value })}><option value="UNKNOWN">Unknown</option><option value="MILD">Mild</option><option value="MODERATE">Moderate</option><option value="SEVERE">Severe</option><option value="LIFE_THREATENING">Life-threatening</option></select></label><label>Onset date<input type="date" value={form.onset_date} onChange={e => setForm({ ...form, onset_date: e.target.value })} /></label><label className="form-span-2">Clinical notes<textarea rows={3} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></label><div><button className="button" disabled={saving || !form.allergen.trim()}>{saving ? "Saving…" : "Record allergy"}</button></div></form></section>
  </section>;
}
