import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

type OfflineEvent = {
  id: string;
  event_type: string;
  status: string;
  attempts: number;
  idempotency_key: string;
  next_retry_at?: string | null;
  created_at?: string | null;
};

type OfflineStats = Record<string, number | string | null | undefined>;

const LOCAL_QUEUE_KEY = "afyasync:offline-clinic-queue";

export function OfflineClinicPage() {
  const [stats, setStats] = useState<OfflineStats>({});
  const [events, setEvents] = useState<OfflineEvent[]>([]);
  const [online, setOnline] = useState(typeof navigator !== "undefined" ? navigator.onLine : true);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [eventType, setEventType] = useState("CLINIC_NOTE");
  const [payload, setPayload] = useState('{"note":"Offline clinic draft"}');
  const [localQueue, setLocalQueue] = useState<Array<{ id: string; event_type: string; payload: unknown; created_at: string }>>(() => {
    try { return JSON.parse(localStorage.getItem(LOCAL_QUEUE_KEY) || "[]"); } catch { return []; }
  });

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [s, p] = await Promise.all([api.offlineStats(), api.offlinePending()]);
      setStats(s || {});
      setEvents((p?.events || []) as OfflineEvent[]);
      setMessage("");
    } catch (error: any) {
      setMessage(error?.message || error?.code || "Unable to load offline status.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    const onOnline = () => setOnline(true);
    const onOffline = () => setOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    void refresh();
    return () => { window.removeEventListener("online", onOnline); window.removeEventListener("offline", onOffline); };
  }, [refresh]);

  const persistLocal = (next: typeof localQueue) => {
    setLocalQueue(next);
    localStorage.setItem(LOCAL_QUEUE_KEY, JSON.stringify(next));
  };

  const queueLocally = () => {
    try {
      const parsed = JSON.parse(payload);
      const next = [...localQueue, { id: crypto.randomUUID(), event_type: eventType, payload: parsed, created_at: new Date().toISOString() }];
      persistLocal(next);
      setMessage("Saved to this device. It will remain available even if the network drops.");
    } catch { setMessage("Payload must be valid JSON."); }
  };

  const enqueue = async () => {
    try {
      setBusy(true);
      const parsed = JSON.parse(payload);
      await api.offlineEnqueue({ event_type: eventType, payload: parsed, idempotency_key: crypto.randomUUID() });
      setMessage("Event queued for synchronisation.");
      await refresh();
    } catch (error: any) {
      setMessage(error?.message || error?.code || "Could not queue event. Save it locally instead.");
    } finally { setBusy(false); }
  };

  const drain = async () => {
    try {
      setBusy(true);
      const result = await api.offlineDrain();
      setMessage(`Synchronisation complete. ${result?.processed ?? 0} event(s) processed.`);
      await refresh();
    } catch (error: any) {
      setMessage(error?.message || error?.code || "Synchronisation failed.");
    } finally { setBusy(false); }
  };

  const probe = async () => {
    try {
      setBusy(true);
      await api.offlineProbe("AfyaSync API", online, undefined, online ? "Browser connectivity reported online" : "Browser is offline");
      setMessage("Connectivity probe recorded.");
      await refresh();
    } catch (error: any) { setMessage(error?.message || error?.code || "Probe failed."); }
    finally { setBusy(false); }
  };

  const pendingCount = useMemo(() => events.filter(e => e.status === "PENDING").length, [events]);

  return <section>
    <div className="page-header">
      <div><p className="eyebrow">OFFLINE-FIRST CLINIC</p><h1>Clinic resilience</h1><p className="muted">Keep frontline work moving through weak or interrupted connectivity, then synchronise safely when the connection returns.</p></div>
      <div className="page-actions"><button className="secondary-button" onClick={() => void refresh()} disabled={loading}>Refresh</button><button className="primary-button" onClick={() => void drain()} disabled={busy || !online}>Synchronise</button></div>
    </div>
    {message && <div className="notice">{message}</div>}
    <div className="stat-grid">
      <div className="stat-card"><span>Connection</span><strong>{online ? "Online" : "Offline"}</strong><small>{online ? "API connection available" : "Local work can still be queued"}</small></div>
      <div className="stat-card"><span>Pending sync</span><strong>{pendingCount}</strong><small>Server-side outbox events</small></div>
      <div className="stat-card"><span>Device queue</span><strong>{localQueue.length}</strong><small>Saved locally in this browser</small></div>
      <div className="stat-card"><span>Server total</span><strong>{String(stats.total ?? stats.pending ?? "—")}</strong><small>Reported by offline service</small></div>
    </div>
    <div className="dashboard-grid">
      <div className="panel">
        <div className="panel-header"><div><h2>Offline clinical queue</h2><p className="muted">Create a safe, idempotent event for the server outbox.</p></div><span className={online ? "status-pill ok" : "status-pill warning"}>{online ? "CONNECTED" : "OFFLINE"}</span></div>
        <label>Event type<input value={eventType} onChange={e => setEventType(e.target.value)} maxLength={80} /></label>
        <label>Payload<textarea rows={7} value={payload} onChange={e => setPayload(e.target.value)} /></label>
        <div className="button-row"><button className="secondary-button" onClick={queueLocally}>Save on device</button><button className="primary-button" onClick={() => void enqueue()} disabled={busy || !online}>Queue for sync</button></div>
      </div>
      <div className="panel">
        <div className="panel-header"><div><h2>Connectivity</h2><p className="muted">Record a connectivity check for operations and troubleshooting.</p></div></div>
        <div className="connectivity-card"><div className="connection-indicator" /><div><strong>{online ? "Network available" : "Network unavailable"}</strong><p className="muted">{online ? "You can synchronise the server outbox." : "Continue with local queueing until service returns."}</p></div></div>
        <button className="secondary-button" onClick={() => void probe()} disabled={busy}>Record connectivity probe</button>
      </div>
    </div>
    <div className="panel">
      <div className="panel-header"><div><h2>Server outbox</h2><p className="muted">Events waiting for reliable processing.</p></div></div>
      {loading ? <p className="muted">Loading…</p> : events.length === 0 ? <div className="empty-state">No pending server events.</div> : <div className="table-wrap"><table><thead><tr><th>Type</th><th>Status</th><th>Attempts</th><th>Created</th><th>Next retry</th></tr></thead><tbody>{events.map(e => <tr key={e.id}><td><strong>{e.event_type}</strong></td><td>{e.status}</td><td>{e.attempts}</td><td>{e.created_at ? new Date(e.created_at).toLocaleString() : "—"}</td><td>{e.next_retry_at ? new Date(e.next_retry_at).toLocaleString() : "Ready"}</td></tr>)}</tbody></table></div>}
    </div>
  </section>;
}
