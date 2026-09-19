import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

type Thread = {
  facility_id: string;
  facility_name: string;
  last_message: string;
};
type Msg = { id: string; sender_type: string; body: string };
type Facility = { id: string; name: string };

export function PatientMessagesPage() {
  const auth = useAuth();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [activeFacility, setActiveFacility] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [body, setBody] = useState("");
  const [newFacilityId, setNewFacilityId] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function loadThreads() {
    const [t, f] = await Promise.all([api.portalMessageThreads(), api.portalFacilities()]);
    setThreads(t);
    setFacilities(f);
  }

  async function openThread(facilityId: string) {
    setActiveFacility(facilityId);
    const msgs = await api.portalMessageThread(facilityId);
    setMessages(msgs);
  }

  useEffect(() => {
    if (auth.accountType !== "patient") return;
    loadThreads().catch(() => setError("Unable to load messages."));
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

  async function send(e: FormEvent) {
    e.preventDefault();
    const facilityId = activeFacility || newFacilityId;
    if (!facilityId || !body.trim()) return;
    setError(null);
    try {
      await api.portalSendMessage({ facility_id: facilityId, body: body.trim() });
      setBody("");
      setNewFacilityId("");
      await openThread(facilityId);
      await loadThreads();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "Send failed");
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
              <h1>Messages</h1>
            </div>
          </div>
          <p className="muted">Message any facility. They can reply from their workspace.</p>

          <div className="portal-actions">
            {threads.map((t) => (
              <button
                key={t.facility_id}
                type="button"
                className={`portal-thread-btn${activeFacility === t.facility_id ? " active" : ""}`}
                onClick={() => void openThread(t.facility_id)}
              >
                <strong>{t.facility_name}</strong>
                <div className="muted small">{t.last_message}</div>
              </button>
            ))}
          </div>

          {activeFacility && (
            <div className="portal-chat">
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={`portal-bubble ${m.sender_type === "PATIENT" ? "patient" : "facility"}`}
                >
                  <div className="who">{m.sender_type === "PATIENT" ? "You" : "Facility"}</div>
                  {m.body}
                </div>
              ))}
            </div>
          )}

          <form className="portal-form" onSubmit={send}>
            {!activeFacility && (
              <label>
                Start conversation with hospital
                <select value={newFacilityId} onChange={(e) => setNewFacilityId(e.target.value)}>
                  <option value="">Select…</option>
                  {facilities.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              Message
              <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={3} required />
            </label>
            {error && <div className="error">{error}</div>}
            <button type="submit" disabled={!body.trim() || (!activeFacility && !newFacilityId)}>
              Send
            </button>
          </form>

          <div className="portal-footer-links">
            <Link to="/portal">Back to portal</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
