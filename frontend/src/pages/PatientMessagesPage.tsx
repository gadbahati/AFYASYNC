import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

type Thread = { facility_id: string; facility_name: string; last_message: string };
type Msg = { id: string; sender_type: string; body: string; template_code?: string | null };
type Facility = { id: string; name: string };
type Template = { code: string; label: string; body: string; slots: string[]; max_slot_len: number };

export function PatientMessagesPage() {
  const auth = useAuth();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [activeFacility, setActiveFacility] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [templateCode, setTemplateCode] = useState("");
  const [slots, setSlots] = useState<Record<string, string>>({});
  const [newFacilityId, setNewFacilityId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadThreads() {
    const [t, f, tpl] = await Promise.all([
      api.portalMessageThreads(),
      api.portalFacilities(),
      api.portalMessageTemplates(),
    ]);
    setThreads(Array.isArray(t) ? t : []);
    setFacilities(Array.isArray(f) ? f : []);
    setTemplates(Array.isArray(tpl) ? tpl : []);
    if (Array.isArray(tpl) && tpl.length && !templateCode) setTemplateCode(tpl[0].code);
  }

  async function openThread(facilityId: string) {
    setActiveFacility(facilityId);
    const msgs = await api.portalMessageThread(facilityId);
    setMessages(Array.isArray(msgs) ? msgs : []);
  }

  useEffect(() => {
    if (auth.accountType !== "patient") return;
    void loadThreads().catch(() => setError("Unable to load messages"));
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

  const selected = templates.find((t) => t.code === templateCode);

  async function send(e: FormEvent) {
    e.preventDefault();
    const facilityId = activeFacility || newFacilityId;
    if (!facilityId || !templateCode) return;
    setError(null);
    setBusy(true);
    try {
      await api.portalSendMessage({
        facility_id: facilityId,
        template_code: templateCode,
        slots: selected?.slots?.length ? slots : undefined,
      });
      setSlots({});
      if (!activeFacility) setActiveFacility(facilityId);
      await openThread(facilityId);
      await loadThreads();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "Send failed");
    } finally {
      setBusy(false);
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
          <p className="muted small">
            Safe template messages only — no free-text. This protects your privacy and keeps hospital
            inboxes focused.
          </p>
          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}

          <h3>Threads</h3>
          {threads.length === 0 ? (
            <p className="muted small">No conversations yet. Start one below.</p>
          ) : (
            <div className="portal-actions">
              {threads.map((th) => (
                <button
                  key={th.facility_id}
                  type="button"
                  className={activeFacility === th.facility_id ? "portal-thread-btn active" : "portal-thread-btn"}
                  onClick={() => void openThread(th.facility_id)}
                >
                  <strong>{th.facility_name}</strong>
                  <span className="muted small">{th.last_message}</span>
                </button>
              ))}
            </div>
          )}

          {activeFacility && (
            <div className="portal-chat">
              {messages.map((m) => (
                <div key={m.id} className={`portal-bubble ${m.sender_type === "PATIENT" ? "patient" : "facility"}`}>
                  <div className="who">{m.sender_type === "PATIENT" ? "You" : "Facility"}</div>
                  {m.body}
                </div>
              ))}
            </div>
          )}

          <form className="portal-form" onSubmit={send}>
            {!activeFacility && (
              <label>
                Facility
                <select value={newFacilityId} onChange={(e) => setNewFacilityId(e.target.value)} required>
                  <option value="">Select facility…</option>
                  {facilities.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              Message template
              <select
                value={templateCode}
                onChange={(e) => {
                  setTemplateCode(e.target.value);
                  setSlots({});
                }}
                required
              >
                {templates.map((t) => (
                  <option key={t.code} value={t.code}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>
            {selected && <p className="muted small">{selected.body}</p>}
            {selected?.slots?.map((slot) => (
              <label key={slot}>
                {slot.replace(/_/g, " ")}
                <input
                  value={slots[slot] || ""}
                  maxLength={selected.max_slot_len || 80}
                  onChange={(e) => setSlots((s) => ({ ...s, [slot]: e.target.value }))}
                  required
                />
              </label>
            ))}
            <button type="submit" disabled={busy}>
              Send template
            </button>
          </form>

          <div className="portal-footer-links">
            <Link to="/portal">← Portal home</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
