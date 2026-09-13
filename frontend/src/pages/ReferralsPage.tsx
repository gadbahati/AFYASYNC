import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Referral } from "../api/types";

export function ReferralsPage() {
  const [rows, setRows] = useState<Referral[]>([]);
  const [role, setRole] = useState<"all" | "source" | "destination">("all");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.listReferrals(role)
      .then((response) => setRows(response.items))
      .catch((err) => setError(err instanceof ApiError ? err.code : "LOAD_FAILED"))
      .finally(() => setLoading(false));
  }, [role]);

  async function decide(id: string, status: "ACCEPTED" | "DECLINED") {
    try {
      const updated = await api.updateReferralStatus(id, status);
      setRows((current) => current.map((item) => item.id === id ? updated : item));
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "UPDATE_FAILED");
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Continuity & transfer</p>
          <h1>Referrals & transfers</h1>
          <p className="muted">Manage real patient referrals between facilities with receiving-facility decisions and an auditable status trail.</p>
        </div>
        <div className="form-actions">
          <button className={role === "all" ? "button" : "button secondary"} onClick={() => setRole("all")}>All</button>
          <button className={role === "source" ? "button" : "button secondary"} onClick={() => setRole("source")}>Sent</button>
          <button className={role === "destination" ? "button" : "button secondary"} onClick={() => setRole("destination")}>Receiving</button>
        </div>
      </header>
      {error && <div className="error">{error}</div>}
      {loading ? <p>Loading referrals…</p> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Referral</th><th>Patient</th><th>From</th><th>To</th><th>Reason</th><th>Status</th><th>Receiving action</th></tr></thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.referral_id}</td>
                  <td>{row.patient_id}</td>
                  <td>{row.source_facility_id}</td>
                  <td>{row.destination_facility_id}</td>
                  <td>{row.reason}</td>
                  <td><span className={row.status === "DECLINED" ? "badge" : "status-pill"}>{row.status}</span></td>
                  <td>{row.status === "SENT" || row.status === "CREATED" ? (
                    <div className="form-actions">
                      <button onClick={() => decide(row.id, "ACCEPTED")}>Accept</button>
                      <button className="button secondary" onClick={() => decide(row.id, "DECLINED")}>Decline</button>
                    </div>
                  ) : <span className="muted">No action</span>}</td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={7} className="muted">No referrals for this facility.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
