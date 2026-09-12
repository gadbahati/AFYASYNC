import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Patient } from "../api/types";

export function PatientsPage() {
  const [items, setItems] = useState<Patient[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .listPatients(50, 0)
      .then((data) => {
        if (!cancelled) {
          setItems(data.items);
          setTotal(data.total);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.code : "PATIENTS_LOAD_FAILED");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <header className="page-header">
        <div>
          <h1>Patients</h1>
          <p className="muted">Facility-scoped active enrollments ({total})</p>
        </div>
        <Link className="button" to="/patients/new">Register patient</Link>
      </header>

      {loading && <p>Loading patients…</p>}
      {error && <div className="error">{error}</div>}

      {!loading && !error && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Afya ID</th>
                <th>Name</th>
                <th>Phone</th>
                <th>Sex</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td><Link to={`/patients/${p.id}`}>{p.afya_id}</Link></td>
                  <td>{[p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ")}</td>
                  <td>{p.phone || "—"}</td>
                  <td>{p.sex || "—"}</td>
                  <td>{p.status}</td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={5} className="muted">No patients enrolled at this facility yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
