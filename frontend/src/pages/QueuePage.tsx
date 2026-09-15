import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Patient, QueueEntry } from "../api/types";

export function QueuePage() {
  const [rows, setRows] = useState<QueueEntry[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const patientMap = useMemo(() => new Map(patients.map((p) => [p.id, p])), [patients]);
  const reload = useCallback(async () => {
    const [queue, people] = await Promise.all([api.listQueueEntries(), api.listPatients(100, 0)]);
    setRows(queue);
    setPatients(people.items);
  }, []);

  useEffect(() => {
    let cancelled = false;
    reload().catch((err) => { if (!cancelled) setError(err instanceof ApiError ? err.code : "LOAD_FAILED"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [reload]);

  async function setStatus(entryId: string, status: string) {
    setBusyId(entryId); setError(null);
    try { await api.updateQueueEntryStatus(entryId, status); await reload(); }
    catch (err) { setError(err instanceof ApiError ? err.code : "UPDATE_FAILED"); }
    finally { setBusyId(null); }
  }

  return <section className="page-stack">
    <header className="page-header"><div><p className="eyebrow">Patient flow</p><h1>Queue</h1><p className="muted">Call, receive and complete patients by name. Every queue entry links back to the patient's continuous care journey.</p></div></header>
    {loading && <p>Loading patient queue…</p>}
    {error && <div className="error">{error}</div>}
    {!loading && <div className="table-wrap"><table><thead><tr><th>Patient</th><th>Afya ID</th><th>Queued</th><th>Priority</th><th>Status</th><th>Next action</th></tr></thead><tbody>
      {rows.map((e) => {
        const patient = patientMap.get(e.patient_id);
        const name = patient ? [patient.first_name, patient.middle_name, patient.last_name].filter(Boolean).join(" ") : e.patient_id;
        return <tr key={e.id}>
          <td><Link className="patient-name-link" to={`/patients/${e.patient_id}/journey`}><strong>{name}</strong></Link></td>
          <td>{patient ? <Link to={`/patients/${patient.id}/journey`}>{patient.afya_id}</Link> : "—"}</td>
          <td>{new Date(e.queued_at).toLocaleString()}</td><td>{e.priority}</td><td><span className="status-pill">{e.status}</span></td>
          <td><div className="actions">
            {e.status === "WAITING" && <button type="button" disabled={busyId === e.id} onClick={() => void setStatus(e.id, "CALLED")}>Call patient</button>}
            {e.status === "CALLED" && <button type="button" disabled={busyId === e.id} onClick={() => void setStatus(e.id, "IN_SERVICE")}>Receive patient</button>}
            {e.status === "IN_SERVICE" && <Link className="button secondary" to={`/patients/${e.patient_id}/journey`}>Open care record</Link>}
            {e.status === "IN_SERVICE" && <button type="button" disabled={busyId === e.id} onClick={() => void setStatus(e.id, "COMPLETED")}>Complete station</button>}
            {(e.status === "COMPLETED" || e.status === "CANCELLED" || e.status === "NO_SHOW") && <Link className="button secondary" to={`/patients/${e.patient_id}/journey`}>View journey</Link>}
          </div></td>
        </tr>;
      })}
      {rows.length === 0 && <tr><td colSpan={6} className="muted">No patients are currently queued.</td></tr>}
    </tbody></table></div>}
  </section>;
}
