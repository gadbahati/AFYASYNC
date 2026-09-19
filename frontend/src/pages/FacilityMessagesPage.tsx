import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";

type Thread = {
  patient_id: string;
  patient_name: string;
  last_message: string;
  last_at?: string;
  sender_type?: string;
};
type Msg = { id: string; sender_type: string; body: string; created_at?: string };

export function FacilityMessagesPage() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activePatient, setActivePatient] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadInbox() {
    setLoading(true);
    try {
      const rows = await api.facilityMessageInbox();
      setThreads(Array.isArray(rows) ? rows : []);
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "Unable to load inbox");
    } finally {
      setLoading(false);
    }
  }

  async function openThread(patientId: string) {
    setActivePatient(patientId);
    setError(null);
    try {
      const msgs = await api.facilityMessageThread(patientId);
      setMessages(Array.isArray(msgs) ? msgs : []);
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "Unable to open thread");
    }
  }

  useEffect(() => {
    void loadInbox();
  }, []);

  async function send(e: FormEvent) {
    e.preventDefault();
    if (!activePatient || !body.trim()) return;
    setError(null);
    try {
      await api.facilitySendMessage({ patient_id: activePatient, body: body.trim() });
      setBody("");
      await openThread(activePatient);
      await loadInbox();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "Send failed");
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Patient communication</p>
          <h1>Messages</h1>
          <p className="muted">Reply to patients who contact this facility from the AfyaSync portal.</p>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <div className="two-col">
        <article className="card">
          <h2>Inbox</h2>
          {loading ? (
            <p className="muted">Loading…</p>
          ) : threads.length === 0 ? (
            <p className="muted small">No messages yet.</p>
          ) : (
            <div className="stack">
              {threads.map((t) => (
                <button
                  key={t.patient_id}
                  type="button"
                  className="secondary"
                  style={{
                    justifyContent: "flex-start",
                    textAlign: "left",
                    borderColor:
                      activePatient === t.patient_id ? "var(--brand)" : undefined,
                  }}
                  onClick={() => void openThread(t.patient_id)}
                >
                  <div>
                    <strong>{t.patient_name}</strong>
                    <div className="muted small">{t.last_message}</div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </article>

        <article className="card">
          <h2>Conversation</h2>
          {!activePatient ? (
            <p className="muted small">Select a patient from the inbox.</p>
          ) : (
            <>
              <div
                className="portal-chat"
                style={{ maxHeight: 320, marginBottom: 12, background: "var(--canvas)" }}
              >
                {messages.map((m) => (
                  <div
                    key={m.id}
                    className={`portal-bubble ${m.sender_type === "FACILITY" ? "patient" : "facility"}`}
                  >
                    <div className="who">
                      {m.sender_type === "FACILITY" ? "Facility" : "Patient"}
                    </div>
                    {m.body}
                  </div>
                ))}
              </div>
              <form className="stack" onSubmit={send}>
                <label>
                  Reply
                  <textarea
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    rows={3}
                    required
                    maxLength={5000}
                  />
                </label>
                <button type="submit" disabled={!body.trim()}>
                  Send reply
                </button>
              </form>
            </>
          )}
        </article>
      </div>
    </section>
  );
}
