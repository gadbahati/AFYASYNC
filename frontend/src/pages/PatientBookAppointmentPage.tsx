import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

type Facility = { id: string; name: string; county?: string | null; facility_type?: string };
type RequestRow = {
  id: string;
  facility_id: string;
  status: string;
  reason: string;
  preferred_date?: string | null;
  offered_appointment_at?: string | null;
  facility_response_notes?: string | null;
  created_at: string;
};

export function PatientBookAppointmentPage() {
  const auth = useAuth();
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [requests, setRequests] = useState<RequestRow[]>([]);
  const [facilityId, setFacilityId] = useState("");
  const [reason, setReason] = useState("");
  const [preferredDate, setPreferredDate] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    const [f, r] = await Promise.all([api.portalFacilities(), api.portalAppointmentRequests()]);
    setFacilities(f);
    setRequests(r);
  }

  useEffect(() => {
    if (auth.accountType !== "patient") return;
    load().catch(() => setError("Unable to load facilities or requests."));
  }, [auth.accountType]);

  if (!auth.ready) return <div className="auth-page"><div className="card auth-card"><p className="muted">Loading…</p></div></div>;
  if (auth.accountType !== "patient") return <Navigate to="/login/patient" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    setSubmitting(true);
    try {
      await api.portalBookAppointment({
        facility_id: facilityId,
        reason,
        preferred_date: preferredDate ? new Date(preferredDate).toISOString() : undefined,
        patient_notes: notes || undefined,
      });
      setOk("Request sent. The hospital will accept, propose a time, or decline.");
      setReason("");
      setPreferredDate("");
      setNotes("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "Could not send request.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page" style={{ alignItems: "flex-start", paddingTop: "1.5rem" }}>
      <div className="card auth-card" style={{ maxWidth: "36rem", width: "100%" }}>
        <div className="auth-brand">
          <KenyaFlag />
          <div>
            <div className="brand-kicker">Patient portal</div>
            <h1>Book appointment</h1>
          </div>
        </div>
        <p className="muted">Choose any hospital on AfyaSync. They will reply with a date or decline.</p>

        <form onSubmit={onSubmit} noValidate>
          <label>
            Hospital
            <select value={facilityId} onChange={(e) => setFacilityId(e.target.value)} required>
              <option value="">Select facility…</option>
              {facilities.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}{f.county ? ` — ${f.county}` : ""}
                </option>
              ))}
            </select>
          </label>
          <label>
            Reason for visit
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} required rows={3} minLength={5} />
          </label>
          <label>
            Preferred date/time (optional)
            <input type="datetime-local" value={preferredDate} onChange={(e) => setPreferredDate(e.target.value)} />
          </label>
          <label>
            Notes for the hospital (optional)
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
          </label>
          {error && <div className="error" role="alert">{error}</div>}
          {ok && <p className="muted">{ok}</p>}
          <button type="submit" disabled={submitting || !facilityId || reason.trim().length < 5}>
            {submitting ? "Sending…" : "Send request"}
          </button>
        </form>

        <h3 style={{ marginTop: "1.5rem" }}>Your requests</h3>
        {requests.length === 0 ? (
          <p className="muted small">No requests yet.</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {requests.map((r) => (
              <li key={r.id} style={{ borderTop: "1px solid #e5e7eb", padding: "0.75rem 0" }}>
                <strong>{r.status}</strong>
                <p className="muted small" style={{ margin: "0.25rem 0" }}>{r.reason}</p>
                {r.offered_appointment_at && (
                  <p className="small">Offered time: {new Date(r.offered_appointment_at).toLocaleString()}</p>
                )}
                {r.facility_response_notes && (
                  <p className="small">Hospital note: {r.facility_response_notes}</p>
                )}
              </li>
            ))}
          </ul>
        )}

        <p className="muted small" style={{ marginTop: "1rem" }}>
          <Link to="/portal">Back to portal</Link>
        </p>
      </div>
    </main>
  );
}
