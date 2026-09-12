import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Appointment } from "../api/types";

export function AppointmentsPage() {
  const [rows, setRows] = useState<Appointment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .listAppointments()
      .then((data) => {
        if (!cancelled) setRows(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.code : "LOAD_FAILED");
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
          <h1>Appointments</h1>
          <p className="muted">Facility appointments (scheduled visits)</p>
        </div>
      </header>
      {loading && <p>Loading…</p>}
      {error && <div className="error">{error}</div>}
      {!loading && !error && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Patient ID</th>
                <th>Department ID</th>
                <th>Reason</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id}>
                  <td>{new Date(a.appointment_at).toLocaleString()}</td>
                  <td>{a.patient_id}</td>
                  <td>{a.department_id}</td>
                  <td>{a.reason || "—"}</td>
                  <td>{a.status}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="muted">No appointments yet for this facility.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
