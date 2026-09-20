import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";

type Thread = {
  patient_id: string;
  patient_name: string;
  last_message: string;
  last_at?: string;
  sender_type?: string;
};
type Msg = { id: string; sender_type: string; body: string; template_code?: string | null; created_at?: string };
type Template = { code: string; label: string; body: string; slots: string[]; max_slot_len: number };

export function FacilityMessagesPage() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [activePatient, setActivePatient] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [templateCode, setTemplateCode] = useState("");
  const [slots, setSlots] = useState<Record<string, string>>({});
  const [freeText, setFreeText] = useState("");
  const [useFreeText, setUseFreeText] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function loadInbox() {
    setLoading(true);
    try {
      const [rows, tpl] = await Promise.all([
        api.facilityMessageInbox(),
        api.facilityMessageTemplates(),
      ]);
      setThreads(Array.isArray(rows) ? rows : []);
      setTemplates(Array.isArray(tpl) ? tpl : []);
      if (Array.isArray(tpl) && tpl.length && !templateCode) setTemplateCode(tpl[0].code);
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

  const selected = templates.find((t) => t.code === templateCode);

  async function send(e: FormEvent) {
    e.preventDefault();
    if (!activePatient) return;
    setError(null);
    setBusy(true);
    try {
      if (useFreeText) {
        await api.facilitySendMessage({
          patient_id: activePatient,
          body: freeText.trim(),
        });
        setFreeText("");
      } else {
        await api.facilitySendMessage({
          patient_id: activePatient,
          template_code: templateCode,
          slots: selected?.slots?.length ? slots : undefined,
        });
        setSlots({});
      }
      await openThread(activePatient);
      await loadInbox();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "Send failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Patient communication</p>
          <h1>Messages</h1>
          <p className="muted">
            Prefer approved templates. Short free-text (max 500 chars) is allowed for staff only.
          </p>
        </div>
        <button type="button" className="button secondary" onClick={() => void loadInbox()}>
          Refresh
        </button>
      </header>

      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <p className="muted">Loading inbox…</p>
      ) : (
        <div className="two-column-grid">
          <article className="card">
            <h2>Inbox</h2>
            {threads.length === 0 ? (
              <p className="muted small">No patient threads yet.</p>
            ) : (
              <ul className="portal-list">
                {threads.map((th) => (
                  <li key={th.patient_id} className="portal-list-item">
                    <button
                      type="button"
                      className="portal-thread-btn"
                      onClick={() => void openThread(th.patient_id)}
                    >
                      <strong>{th.patient_name}</strong>
                      <span className="muted small">{th.last_message}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </article>

          <article className="card">
            <h2>{activePatient ? "Conversation" : "Select a patient"}</h2>
            {activePatient && (
              <>
                <div className="portal-chat" style={{ marginBottom: 12 }}>
                  {messages.map((m) => (
                    <div
                      key={m.id}
                      className={`portal-bubble ${m.sender_type === "FACILITY" ? "patient" : "facility"}`}
                    >
                      <div className="who">{m.sender_type}</div>
                      {m.body}
                    </div>
                  ))}
                </div>
                <form className="form-grid" onSubmit={send}>
                  <label className="span-2">
                    <input
                      type="checkbox"
                      checked={useFreeText}
                      onChange={(e) => setUseFreeText(e.target.checked)}
                    />{" "}
                    Use short free-text instead of template
                  </label>
                  {!useFreeText ? (
                    <>
                      <label className="span-2">
                        Template
                        <select
                          value={templateCode}
                          onChange={(e) => {
                            setTemplateCode(e.target.value);
                            setSlots({});
                          }}
                        >
                          {templates.map((t) => (
                            <option key={t.code} value={t.code}>
                              {t.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      {selected && <p className="muted small span-2">{selected.body}</p>}
                      {selected?.slots?.map((slot) => (
                        <label key={slot} className="span-2">
                          {slot.replace(/_/g, " ")}
                          <input
                            value={slots[slot] || ""}
                            maxLength={selected.max_slot_len || 80}
                            onChange={(e) => setSlots((s) => ({ ...s, [slot]: e.target.value }))}
                            required
                          />
                        </label>
                      ))}
                    </>
                  ) : (
                    <label className="span-2">
                      Free text (max 500)
                      <textarea
                        value={freeText}
                        maxLength={500}
                        onChange={(e) => setFreeText(e.target.value)}
                        required
                      />
                    </label>
                  )}
                  <div className="form-actions span-2">
                    <button type="submit" disabled={busy}>
                      Send
                    </button>
                  </div>
                </form>
              </>
            )}
          </article>
        </div>
      )}
    </section>
  );
}
