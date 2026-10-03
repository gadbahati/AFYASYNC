import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Patient, PatientListResponse } from "../api/types";
import { useWorkspace } from "../workspaces/WorkspaceContext";

export function PatientsPage() {
  const { scope } = useWorkspace();
  const [items, setItems] = useState<Patient[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .listPatients(50, 0, scope)
      .then((data: PatientListResponse) => {
        if (!cancelled) {
          setItems(data.items);
          setTotal(data.total);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.code : "PATIENTS_LOAD_FAILED");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [scope]);

  return (
    <div>
      <header className="page-header">
        <div>
          <h1>Patients</h1>
          <p className="muted">
            Patient registry under <strong>{scope}</strong> scope ({total}). Select a patient to open the care journey
            and full clinical record.
          </p>
        </div>
        <div className="actions">
          <Link className="button secondary" to="/workspace">
            Change scope
          </Link>
          <Link className="button secondary" to="/patients/sha-lookup">
            SHA member lookup
          </Link>
          <Link className="button" to="/patients/new">
            Register patient
          </Link>
        </div>
      </header>
      {loading && <p>Loading patients…</p>}
      {error && <div className="error">{error}</div>}
      {!loading && !error && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Afya ID</th>
                <th>Patient name</th>
                <th>Phone</th>
                <th>Sex</th>
                <th>Status</th>
                <th>Journey</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Link to={`/patients/${p.id}/journey`}>{p.afya_id}</Link>
                  </td>
                  <td>
                    <Link className="patient-name-link" to={`/patients/${p.id}/journey`}>
                      <strong>{[p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ")}</strong>
                    </Link>
                  </td>
                  <td>{p.phone || "—"}</td>
                  <td>{p.sex || "—"}</td>
                  <td>
                    <span className="status-pill">{p.status}</span>
                  </td>
                  <td>
                    <Link className="button secondary" to={`/patients/${p.id}/journey`}>
                      Open patient journey
                    </Link>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="muted">
                    No patients found under this operating scope.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
