import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Patient = { id: string; afya_id: string; first_name: string; middle_name?: string | null; last_name: string; phone?: string | null; status: string };
type Department = { id: string; name: string; code: string; status: string };
type Draft = { id: string; patient_id: string; department_id: string; encounter_type: string; coverage_mode: "CASH" | "SHA" | "AFYASYNC" | "OTHER"; reason: string; created_at: string; sync_status: "LOCAL" | "QUEUED" | "SYNCED" | "FAILED"; error?: string };
type OfflineEvent = { id: string; event_type: string; status: string; attempts: number; idempotency_key: string; next_retry_at?: string | null; created_at?: string | null };

const KEY = (kind: string, facilityId: string | null) => "afyasync:offline:" + kind + ":v1:" + (facilityId || "unselected");

function read<T>(key: string, fallback: T): T { try { return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback)); } catch { return fallback; } }
function write(key: string, value: unknown) { localStorage.setItem(key, JSON.stringify(value)); }

export function OfflineClinicPage() {
  const auth = useAuth();
  const [online, setOnline] = useState(navigator.onLine);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [events, setEvents] = useState<OfflineEvent[]>([]);
  const [stats, setStats] = useState<any>({});
  const [selectedPatient, setSelectedPatient] = useState("");
  const [patientSearch, setPatientSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [encounterType, setEncounterType] = useState("OUTPATIENT");
  const [coverageMode, setCoverageMode] = useState<Draft["coverage_mode"]>("CASH");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [cacheLimit, setCacheLimit] = useState(100);
  const [lastCachedAt, setLastCachedAt] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!navigator.onLine || !auth.facilityId) return;
    try {
      const [p, d, s, pending] = await Promise.all([
        api.listPatients(cacheLimit, 0),
        api.listDepartments(auth.facilityId),
        api.offlineStats(),
        api.offlinePending(100),
      ]);
      const ps = (p?.items || []) as Patient[];
      const ds = (d || []) as Department[];
      setPatients(ps); write(KEY("patients", auth.facilityId), ps);
      setDepartments(ds); write(KEY("departments", auth.facilityId), ds);
      setStats(s || {}); setEvents((pending?.events || []) as OfflineEvent[]); setLastCachedAt(new Date().toISOString());
    } catch (e: any) {
      setMessage(e?.message || e?.code || "Offline mode is active. Using cached clinic data.");
    }
  }, [auth.facilityId, cacheLimit]);

  useEffect(() => {
    if (!auth.facilityId) return;
    setPatients(read(KEY("patients", auth.facilityId), []));
    setDepartments(read(KEY("departments", auth.facilityId), []));
    setDrafts(read(KEY("drafts", auth.facilityId), []));
  }, [auth.facilityId]);

  useEffect(() => {
    const onlineHandler = () => { setOnline(true); void refresh(); };
    const offlineHandler = () => setOnline(false);
    window.addEventListener("online", onlineHandler);
    window.addEventListener("offline", offlineHandler);
    void refresh();
    return () => { window.removeEventListener("online", onlineHandler); window.removeEventListener("offline", offlineHandler); };
  }, [refresh]);

  useEffect(() => { if (auth.facilityId) write(KEY("drafts", auth.facilityId), drafts); }, [drafts, auth.facilityId]);

  const visiblePatients = useMemo(() => {
    const q = patientSearch.trim().toLowerCase();
    if (!q) return patients.slice(0, 50);
    return patients.filter(p => [p.afya_id, p.first_name, p.middle_name, p.last_name, p.phone].filter(Boolean).join(" ").toLowerCase().includes(q)).slice(0, 50);
  }, [patients, patientSearch]);

  const selected = patients.find(p => p.id === selectedPatient);
  const pendingLocal = drafts.filter(d => d.sync_status !== "SYNCED").length;
  const pendingServer = events.filter(e => e.status === "PENDING" || e.status === "FAILED").length;

  const saveDraft = () => {
    if (!selectedPatient || !department || !reason.trim()) { setMessage("Select a patient and department and enter the clinical reason."); return; }
    const draft: Draft = { id: crypto.randomUUID(), patient_id: selectedPatient, department_id: department, encounter_type: encounterType, coverage_mode: coverageMode, reason: reason.trim(), created_at: new Date().toISOString(), sync_status: "LOCAL" };
    setDrafts(v => [...v, draft]);
    setReason(""); setMessage("Clinical encounter saved securely on this device. It has not been submitted yet.");
  };

  const queueDraft = async (draft: Draft) => {
    try {
      const key = draft.id;
      await api.offlineEnqueue({ event_type: "CLINICAL_ENCOUNTER", payload: { patient_id: draft.patient_id, department_id: draft.department_id, encounter_type: draft.encounter_type, coverage_mode: draft.coverage_mode, reason: draft.reason }, idempotency_key: key });
      setDrafts(v => v.map(d => d.id === draft.id ? { ...d, sync_status: "QUEUED", error: undefined } : d));
    } catch (e: any) {
      setDrafts(v => v.map(d => d.id === draft.id ? { ...d, sync_status: "FAILED", error: e?.message || e?.code || "Queue failed" } : d));
    }
  };

  const syncLocal = async () => {
    if (!online) { setMessage("Reconnect before synchronising."); return; }
    setBusy(true);
    try {
      for (const draft of drafts.filter(d => d.sync_status === "LOCAL" || d.sync_status === "FAILED")) await queueDraft(draft);
      const result = await api.offlineDrain(100);
      setMessage(`Synchronisation finished: ${result?.processed ?? 0} event(s) processed.`);
      await refresh();
    } finally { setBusy(false); }
  };

  const removeDraft = (id: string) => setDrafts(v => v.filter(d => d.id !== id));

  return <section>
    <div className="page-header">
      <div><p className="eyebrow">PHASE 21 • OFFLINE-FIRST</p><h1>Offline clinic workspace</h1><p className="muted">Continue core registration and encounter work during connectivity loss. Data is stored locally first and synchronised with an idempotent server outbox when connectivity returns.</p></div>
      <div className="page-actions"><span className={online ? "status-pill ok" : "status-pill warning"}>{online ? "ONLINE" : "OFFLINE"}</span><select value={cacheLimit} onChange={e => setCacheLimit(Number(e.target.value))}><option value={100}>Cache 100 patients</option><option value={250}>Cache 250 patients</option><option value={500}>Cache 500 patients</option></select><button className="secondary-button" onClick={() => void refresh()}>Refresh cache</button><button className="primary-button" onClick={() => void syncLocal()} disabled={busy || !online}>{busy ? "Synchronising…" : "Synchronise"}</button></div>
    </div>
    {message && <div className="notice">{message}</div>}
    <div className="stat-grid">
      <div className="stat-card"><span>Connection</span><strong>{online ? "Available" : "Interrupted"}</strong><small>{online ? "Server reachable" : "Local workflow active"}</small></div>
      <div className="stat-card"><span>Cached patients</span><strong>{patients.length}</strong><small>Last successful facility cache</small></div>
      <div className="stat-card"><span>Local drafts</span><strong>{pendingLocal}</strong><small>Waiting for synchronisation</small></div>
      <div className="stat-card"><span>Server outbox</span><strong>{pendingServer}</strong><small>Pending or retryable</small></div><div className="stat-card"><span>Cache refreshed</span><strong>{lastCachedAt ? new Date(lastCachedAt).toLocaleTimeString() : "—"}</strong><small>Local facility snapshot</small></div>
    </div>

    <div className="dashboard-grid">
      <div className="panel">
        <div className="panel-header"><div><h2>Start encounter</h2><p className="muted">Works against the cached patient and department list when offline.</p></div></div>
        <label>Find patient<input value={patientSearch} onChange={e => setPatientSearch(e.target.value)} placeholder="Afya ID, name or phone" /></label>
        <label>Patient<select value={selectedPatient} onChange={e => setSelectedPatient(e.target.value)}><option value="">Select patient</option>{visiblePatients.map(p => <option key={p.id} value={p.id}>{p.afya_id} — {p.first_name} {p.middle_name || ""} {p.last_name}</option>)}</select></label>
        {selected && <div className="notice"><strong>{selected.first_name} {selected.last_name}</strong> · {selected.afya_id}{selected.phone ? ` · ${selected.phone}` : ""}</div>}
        <label>Department<select value={department} onChange={e => setDepartment(e.target.value)}><option value="">Select department</option>{departments.filter(d => d.status === "ACTIVE").map(d => <option key={d.id} value={d.id}>{d.name} ({d.code})</option>)}</select></label>
        <div className="form-grid-2">
          <label>Encounter type<select value={encounterType} onChange={e => setEncounterType(e.target.value)}><option>OUTPATIENT</option><option>EMERGENCY</option><option>INPATIENT</option><option>FOLLOW_UP</option></select></label>
          <label>Coverage<select value={coverageMode} onChange={e => setCoverageMode(e.target.value as Draft["coverage_mode"])}><option value="CASH">Cash</option><option value="SHA">SHA</option><option value="AFYASYNC">AfyaSync</option><option value="OTHER">Other</option></select></label>
        </div>
        <label>Clinical reason<textarea rows={5} value={reason} onChange={e => setReason(e.target.value)} placeholder="Reason for encounter" /></label>
        <button className="primary-button" onClick={saveDraft}>Save encounter locally</button>
      </div>

      <div className="panel">
        <div className="panel-header"><div><h2>Offline safety</h2><p className="muted">The application distinguishes local storage from server acceptance.</p></div></div>
        <div className="connectivity-card"><div className="connection-indicator" /><div><strong>{online ? "Connected" : "Working offline"}</strong><p className="muted">{online ? "New local drafts can be queued and synchronised." : "Do not close or clear this browser profile until drafts are synchronised."}</p></div></div>
        <div className="notice"><strong>Important:</strong> cached data is read-only while offline. New clinical encounters are saved locally and are not treated as server records until synchronisation succeeds.</div>
        <button className="secondary-button" onClick={async () => { setBusy(true); try { await api.offlineProbe("AfyaSync API", online, undefined, online ? "Browser reports connectivity" : "Browser reports offline"); setMessage("Connectivity probe recorded."); } catch (e: any) { setMessage(e?.message || "Probe failed."); } finally { setBusy(false); } }} disabled={busy}>Record connectivity probe</button><button className="secondary-button" onClick={() => { if (!auth.facilityId) return; if (!window.confirm("Clear this facility's offline cache and unsynchronised drafts from this browser?")) return; localStorage.removeItem(KEY("patients", auth.facilityId)); localStorage.removeItem(KEY("departments", auth.facilityId)); localStorage.removeItem(KEY("drafts", auth.facilityId)); setPatients([]); setDepartments([]); setDrafts([]); setMessage("This facility's local cache was cleared. Server records were not changed."); }}>Clear device cache</button>
      </div>
    </div>

    <div className="panel">
      <div className="panel-header"><div><h2>Local encounter queue</h2><p className="muted">Every draft has an explicit synchronisation state.</p></div></div>
      {drafts.length === 0 ? <div className="empty-state">No local encounters.</div> : <div className="table-wrap"><table><thead><tr><th>Patient</th><th>Type</th><th>Coverage</th><th>Created</th><th>State</th><th>Action</th></tr></thead><tbody>{drafts.map(d => { const p=patients.find(x=>x.id===d.patient_id); return <tr key={d.id}><td><strong>{p ? `${p.first_name} ${p.last_name}` : d.patient_id}</strong><br/><span className="muted small">{p?.afya_id || "Patient unavailable in cache"}</span></td><td>{d.encounter_type}</td><td>{d.coverage_mode}</td><td>{new Date(d.created_at).toLocaleString()}</td><td>{d.sync_status}{d.error ? <><br/><span className="muted small">{d.error}</span></> : null}</td><td><div className="button-row">{d.sync_status !== "QUEUED" && <button className="secondary-button" onClick={() => void queueDraft(d)} disabled={!online}>Queue</button>}<button className="linkish" onClick={() => removeDraft(d.id)}>Remove</button></div></td></tr>;})}</tbody></table></div>}
    </div>

    <div className="panel">
      <div className="panel-header"><div><h2>Server outbox</h2><p className="muted">Server-side events awaiting processing or retry.</p></div><span className="status-pill">{String(stats.synced ?? 0)} synced</span></div>
      {events.length === 0 ? <div className="empty-state">No pending server events.</div> : <div className="table-wrap"><table><thead><tr><th>Type</th><th>Status</th><th>Attempts</th><th>Created</th><th>Retry</th></tr></thead><tbody>{events.map(e => <tr key={e.id}><td>{e.event_type}</td><td>{e.status}</td><td>{e.attempts}</td><td>{e.created_at ? new Date(e.created_at).toLocaleString() : "—"}</td><td>{e.next_retry_at ? new Date(e.next_retry_at).toLocaleString() : "Ready"}</td></tr>)}</tbody></table></div>}
    </div>
  </section>;
}
