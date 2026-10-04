import { useState } from "react";
import { api } from "../api/client";

type Candidate = {
  patient_id: string;
  afya_id: string;
  full_name: string;
  date_of_birth: string | null;
  phone: string | null;
  match_score: number;
  match_reasons: string[];
};

export function CrossFacilityRecordPage() {
  const [nationalId, setNationalId] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [dob, setDob] = useState("");
  const [phone, setPhone] = useState("");
  const [reason, setReason] = useState("");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [record, setRecord] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function search() {
    setLoading(true); setError(""); setCandidates([]); setRecord(null);
    try {
      const result = await api.crossFacilityMpiCandidates({
        national_id_number: nationalId.trim() || undefined,
        first_name: firstName.trim() || undefined,
        last_name: lastName.trim() || undefined,
        date_of_birth: dob || undefined,
        phone: phone.trim() || undefined,
      });
      setCandidates(result?.candidates || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "CROSS_FACILITY_MPI_FAILED");
    } finally { setLoading(false); }
  }

  async function openRecord(patientId: string) {
    if (reason.trim().length < 3) { setError("Enter an access reason before opening a cross-facility record."); return; }
    setLoading(true); setError("");
    try { setRecord(await api.crossFacilityPatientRecord(patientId, reason.trim())); }
    catch (e) { setError(e instanceof Error ? e.message : "CROSS_FACILITY_RECORD_FAILED"); }
    finally { setLoading(false); }
  }

  return <section className="page-stack">
    <div className="page-header">
      <div>
        <p className="eyebrow">Phase 162 · MPI & continuity</p>
        <h1>Cross-facility patient record</h1>
        <p className="muted">Find an existing patient identity across your authorised facility network and review the longitudinal record without creating a duplicate identity.</p>
      </div>
    </div>

    <div className="card">
      <div className="card-header"><div><h2>Master Patient Index search</h2><p className="muted">Use the strongest available identifiers. Matching is performed against protected identity data; raw national ID values are never returned.</p></div><span className="status-badge">NETWORK SCOPE</span></div>
      <div className="form-grid">
        <label>National ID<input value={nationalId} onChange={e=>setNationalId(e.target.value.replace(/\D/g,"").slice(0,9))} inputMode="numeric" autoComplete="off" /></label>
        <label>First name<input value={firstName} onChange={e=>setFirstName(e.target.value)} /></label>
        <label>Last name<input value={lastName} onChange={e=>setLastName(e.target.value)} /></label>
        <label>Date of birth<input type="date" value={dob} onChange={e=>setDob(e.target.value)} /></label>
        <label>Phone<input value={phone} onChange={e=>setPhone(e.target.value)} autoComplete="off" /></label>
        <label>Access reason<textarea value={reason} onChange={e=>setReason(e.target.value)} minLength={3} maxLength={200} rows={2} placeholder="e.g. continuity of care" /></label>
      </div>
      <div className="form-actions"><button className="primary" disabled={loading || ![nationalId,firstName,lastName,dob,phone].some(v=>v.trim())} onClick={()=>void search()}>{loading ? "Searching…" : "Find patient"}</button></div>
      {error && <div className="error-banner" role="alert">{error}</div>}
    </div>

    {candidates.length > 0 && <div className="card">
      <div className="card-header"><div><h2>Identity matches</h2><p className="muted">A match does not automatically grant access to the clinical record. Select the correct identity and provide a lawful access reason.</p></div></div>
      <div className="table-wrap"><table><thead><tr><th>Afya ID</th><th>Patient</th><th>DOB</th><th>Match</th><th>Action</th></tr></thead>
      <tbody>{candidates.map(c=><tr key={c.patient_id}><td>{c.afya_id}</td><td>{c.full_name}</td><td>{c.date_of_birth || "—"}</td><td>{c.match_score}% · {c.match_reasons.join(", ")}</td><td><button disabled={loading || reason.trim().length < 3} onClick={()=>void openRecord(c.patient_id)}>Open authorised record</button></td></tr>)}</tbody></table></div>
    </div>}

    {record && <div className="card">
      <div className="card-header"><div><p className="eyebrow">Authorised longitudinal view</p><h2>{record.patient_id}</h2><p className="muted">{record.source_facility_count} facility record source(s) · reason: {record.access_reason}</p></div><span className="status-badge">AUDITED</span></div>
      {record.records.map((source:any)=><details key={source.facility_id} open className="card" style={{marginTop:12}}>
        <summary><strong>Facility {source.facility_id}</strong></summary>
        <pre style={{whiteSpace:"pre-wrap",overflowX:"auto"}}>{JSON.stringify(source.record, null, 2)}</pre>
      </details>)}
    </div>}
  </section>;
}
