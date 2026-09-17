import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Patient, PatientListResponse } from "../api/types";

export function PatientsPage() {
  const [items, setItems] = useState<Patient[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.listPatients(50, 0).then((data: PatientListResponse) => { if (!cancelled) { setItems(data.items); setTotal(data.total); } })
      .catch((err: unknown) => { if (!cancelled) setError(err instanceof ApiError ? err.code : "PATIENTS_LOAD_FAILED"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return <div>
    <header className="page-header"><div><h1>Patients</h1><p className="muted">Facility-scoped patient registry ({total}). Select a patient's name to open the live end-to-end care journey and full clinical record.</p></div><div className="actions"><Link className="button secondary" to="/patients/sha-lookup">SHA member lookup</Link><Link className="button" to="/patients/new">Register patient</Link></div></header>
    {loading && <p>Loading patients…</p>}{error && <div className="error">{error}</div>}
    {!loading && !error && <div className="table-wrap"><table><thead><tr><th>Afya ID</th><th>Patient name</th><th>Phone</th><th>Sex</th><th>Status</th><th>Journey</th></tr></thead><tbody>{items.map((p) => <tr key={p.id}><td><Link to={`/patients/${p.id}/journey`}>{p.afya_id}</Link></td><td><Link className="patient-name-link" to={`/patients/${p.id}/journey`}><strong>{[p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ")}</strong></Link></td><td>{p.phone || "—"}</td><td>{p.sex || "—"}</td><td><span className="status-pill">{p.status}</span></td><td><Link className="button secondary" to={`/patients/${p.id}/journey`}>Open patient journey</Link></td></tr>)}{items.length === 0 && <tr><td colSpan={6} className="muted">No patients enrolled at this facility yet.</td></tr>}</tbody></table></div>}
  </div>;
}
