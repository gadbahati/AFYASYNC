import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

type Facility = { id: string; name: string; county?: string | null };
type RequestRow = {
  id: string;
  status: string;
  reason: string;
  offered_appointment_at?: string | null;
  facility_response_notes?: string | null;
};

function statusClass(status: string): string {
  const s = status.toLowerCase();
  if (s === "pending") return "pending";
  if (s === "accepted" || s === "rescheduled") return "accepted";
  if (s.includes("declined") || s.includes("cancel")) return "declined";
  return "";
}

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

  if (!auth.ready) {
    return (
      <div className="portal-page">
        <div className="portal-shell">
          <div className="portal-card">
            <p className="muted">Loading…</p>
          </div>
        </div>
      </div>
    );
  }
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
    <div className="portal-page">
      <div className="portal-shell wide">
        <div className="portal-card">
          <div className="portal-brand">
            <KenyaFlag />
            <div>
              <div className="brand-kicker">Patient portal</div>
              <h1>Book appointment</h1>
            </div>
          </div>
          <p className="muted">Choose any hospital on AfyaSync. They will reply with a date or decline.</p>

          <form className="portal-form" onSubmit={onSubmit} noValidate>
            <label>
              Hospital
              <select value={facilityId} onChange={(e) => setFacilityId(e.target.value)} required>
                <option value="">Select facility…</option>
                {facilities.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                    {f.county ? ` — ${f.county}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Reason for visit
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                required
                rows={3}
                minLength={5}
              />
            </label>
            <label>
              Preferred date/time (optional)
              <input
                type="datetime-local"
                value={preferredDate}
                onChange={(e) => setPreferredDate(e.target.value)}
              />
            </label>
            <label>
              Notes for the hospital (optional)
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
            </label>
            {error && (
              <div className="error" role="alert">
                {error}
              </div>
            )}
            {ok && <div className="success-box">{ok}</div>}
            <button type="submit" disabled={submitting || !facilityId || reason.trim().length < 5}>
              {submitting ? "Sending…" : "Send request"}
            </button>
          </form>

          <h3>Your requests</h3>
          {requests.length === 0 ? (
            <p className="muted small">No requests yet.</p>
          ) : (
            <ul className="portal-list">
              {requests.map((r) => (
                <li key={r.id} className="portal-list-item">
                  <span className={`portal-status ${statusClass(r.status)}`}>{r.status}</span>
                  <p className="muted small" style={{ marginTop: 6 }}>
                    {r.reason}
                  </p>
                  {r.offered_appointment_at && (
                    <p className="small">
                      Offered time: {new Date(r.offered_appointment_at).toLocaleString()}
                    </p>
                  )}
                  {r.facility_response_notes && (
                    <p className="small">Hospital note: {r.facility_response_notes}</p>
                  )}
                </li>
              ))}
            </ul>
          )}

          <div className="portal-footer-links">
            <Link to="/portal">Back to portal</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
