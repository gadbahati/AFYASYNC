import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { Referral } from "../api/types";

export function ReferralsPage() {
  const [rows, setRows] = useState<Referral[]>([]);
  const [role, setRole] = useState<"all" | "source" | "destination">("all");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    encounter_id: "",
    destination_facility_id: "",
    reason: "",
    priority: "ROUTINE",
    clinical_summary: "",
  });

  function load() {
    setLoading(true);
    setError(null);
    api.listReferrals(role)
      .then((response) => setRows(response.items))
      .catch((err) => setError(err instanceof ApiError ? err.code : "LOAD_FAILED"))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [role]);

  async function decide(id: string, status: "ACCEPTED" | "DECLINED") {
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateReferralStatus(id, status);
      setRows((current) => current.map((item) => (item.id === id ? updated : item)));
      setMessage(`Referral ${status.toLowerCase()}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "UPDATE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.createReferral({
        encounter_id: form.encounter_id.trim(),
        destination_facility_id: form.destination_facility_id.trim(),
        reason: form.reason.trim(),
        priority: form.priority,
        clinical_summary: form.clinical_summary.trim() || null,
      });
      setForm({ encounter_id: "", destination_facility_id: "", reason: "", priority: "ROUTINE", clinical_summary: "" });
      setMessage("Referral created");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "CREATE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Continuity & transfer</p>
          <h1>Referrals & transfers</h1>
          <p className="muted">
            Create referrals from an open encounter, then let the receiving facility accept or decline — fully on the live API.
          </p>
        </div>
        <div className="form-actions">
          <button type="button" className={role === "all" ? "button" : "button secondary"} onClick={() => setRole("all")}>All</button>
          <button type="button" className={role === "source" ? "button" : "button secondary"} onClick={() => setRole("source")}>Sent</button>
          <button type="button" className={role === "destination" ? "button" : "button secondary"} onClick={() => setRole("destination")}>Receiving</button>
        </div>
      </header>
      {error && <div className="error">{error}</div>}
      {message && <div className="success-box">{message}</div>}

      <article className="card">
        <h2>Create referral</h2>
        <p className="muted">Requires a real encounter at this facility and a destination facility ID.</p>
        <form className="form-grid" onSubmit={onCreate}>
          <label className="full">Encounter ID
            <input required value={form.encounter_id} onChange={(e) => setForm({ ...form, encounter_id: e.target.value })} placeholder="Encounter UUID" />
          </label>
          <label className="full">Destination facility ID
            <input required value={form.destination_facility_id} onChange={(e) => setForm({ ...form, destination_facility_id: e.target.value })} placeholder="Facility UUID" />
          </label>
          <label>Priority
            <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
              <option value="ROUTINE">Routine</option>
              <option value="URGENT">Urgent</option>
              <option value="EMERGENCY">Emergency</option>
            </select>
          </label>
          <label>Reason
            <input required value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} placeholder="Why is the patient being referred?" />
          </label>
          <label className="full">Clinical summary
            <textarea value={form.clinical_summary} onChange={(e) => setForm({ ...form, clinical_summary: e.target.value })} placeholder="Key findings, treatment so far, what is needed at receiving facility" />
          </label>
          <div className="full actions">
            <button type="submit" disabled={busy}>{busy ? "Submitting…" : "Create referral"}</button>
          </div>
        </form>
      </article>

      {loading ? <p>Loading referrals…</p> : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Referral</th>
                <th>Patient</th>
                <th>From</th>
                <th>To</th>
                <th>Reason</th>
                <th>Status</th>
                <th>Receiving action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.referral_id}</td>
                  <td>{row.patient_id}</td>
                  <td>{row.source_facility_id}</td>
                  <td>{row.destination_facility_id}</td>
                  <td>{row.reason}</td>
                  <td><span className={row.status === "DECLINED" ? "badge" : "status-pill"}>{row.status}</span></td>
                  <td>
                    {row.status === "SENT" || row.status === "CREATED" ? (
                      <div className="form-actions">
                        <button type="button" disabled={busy} onClick={() => decide(row.id, "ACCEPTED")}>Accept</button>
                        <button type="button" className="button secondary" disabled={busy} onClick={() => decide(row.id, "DECLINED")}>Decline</button>
                      </div>
                    ) : (
                      <span className="muted">No action</span>
                    )}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><td colSpan={7} className="muted">No referrals for this facility.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
