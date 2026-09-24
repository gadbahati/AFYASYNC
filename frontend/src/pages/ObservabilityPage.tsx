import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

type Runtime = {
  started_at: string; requests: number; errors: number; client_errors: number;
  server_errors: number; error_rate: number; server_error_rate: number;
  timed_requests: number; average_duration_seconds: number; max_duration_seconds: number;
};
type Slo = {
  id: string; name: string; ok: boolean; observed: number; target?: number;
  target_max?: number; target_max_seconds?: number; sample_requests?: number;
  timed_requests?: number; warmup?: boolean;
};
type SloResponse = { slos: Slo[]; all_ok: boolean; band: string; runtime: Runtime; note: string; generated_at: string };
type Hooks = {
  request_id: { header_in: string; header_out: string; behavior: string; middleware: string };
  privacy: string;
  metrics: { module: string; recorded: string[] };
  external_apm: string;
};

function pct(value: number) { return (value * 100).toFixed(2) + "%"; }
function seconds(value: number) { return value.toFixed(3) + " s"; }

export function ObservabilityPage() {
  const [runtime, setRuntime] = useState<Runtime | null>(null);
  const [slos, setSlos] = useState<SloResponse | null>(null);
  const [hooks, setHooks] = useState<Hooks | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [r, s, h] = await Promise.all([
        api.observabilityRuntime(),
        api.observabilitySlos(),
        api.observabilityTracingHooks(),
      ]);
      setRuntime(r?.data ?? r);
      setSlos(s);
      setHooks(h);
    } catch (err: any) {
      setError(err?.message || "Observability data could not be loaded.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return <section className="page-stack">
    <div className="page-heading">
      <div>
        <span className="eyebrow">PHASE 32 • OBSERVABILITY & SLOs</span>
        <h1>Observability</h1>
        <p className="muted">Runtime request metrics, service-level objectives and request-correlation controls.</p>
      </div>
      <button type="button" onClick={() => void load()} disabled={loading}>{loading ? "Refreshing…" : "Refresh"}</button>
    </div>

    {error && <div className="warning-box" role="alert">{error}</div>}

    <div className="card-grid">
      <article className="card"><span className="eyebrow">REQUESTS</span><strong className="stat-value">{runtime?.requests ?? "—"}</strong><span className="muted">requests observed by this process</span></article>
      <article className="card"><span className="eyebrow">SERVER ERRORS</span><strong className="stat-value">{runtime ? pct(runtime.server_error_rate) : "—"}</strong><span className="muted">{runtime?.server_errors ?? "—"} 5xx responses</span></article>
      <article className="card"><span className="eyebrow">AVG LATENCY</span><strong className="stat-value">{runtime ? seconds(runtime.average_duration_seconds) : "—"}</strong><span className="muted">{runtime?.timed_requests ?? "—"} timed requests</span></article>
      <article className="card"><span className="eyebrow">SLO POSTURE</span><strong className="stat-value">{slos?.band ?? "—"}</strong><span className="muted">{slos ? (slos.all_ok ? "All evaluated objectives passing" : "One or more objectives need attention") : "Loading objectives"}</span></article>
    </div>

    <article className="card">
      <div className="row-between"><div><span className="eyebrow">SERVICE-LEVEL OBJECTIVES</span><h2>Current SLO evaluation</h2><p className="muted">Objectives use process-local samples and warm-up grace where documented by the backend.</p></div><span className="status-pill">{slos?.band ?? "—"}</span></div>
      <div className="table-wrap"><table><thead><tr><th>Objective</th><th>Status</th><th>Observed</th><th>Target</th><th>Sample</th></tr></thead><tbody>
        {(slos?.slos || []).map(item => <tr key={item.id}>
          <td><strong>{item.name}</strong><br/><span className="muted small">{item.id}</span></td>
          <td><span className={"status-pill" + (item.ok ? "" : " warning")}>{item.ok ? "PASS" : "CHECK"}</span></td>
          <td>{item.id === "SLO-AVAILABILITY" ? pct(item.observed) : item.id === "SLO-ERROR-RATE" ? pct(item.observed) : seconds(item.observed)}</td>
          <td>{item.target !== undefined ? "≥ " + pct(item.target) : item.target_max !== undefined ? "≤ " + pct(item.target_max) : "≤ " + seconds(item.target_max_seconds ?? 0)}</td>
          <td>{item.sample_requests ?? item.timed_requests ?? 0}{item.warmup ? " (warm-up)" : ""}</td>
        </tr>)}
      </tbody></table></div>
    </article>

    <div className="card-grid">
      <article className="card">
        <span className="eyebrow">RUNTIME DETAIL</span><h2>Process metrics</h2>
        <dl className="detail-list">
          <div><dt>Started</dt><dd>{runtime ? new Date(runtime.started_at).toLocaleString() : "—"}</dd></div>
          <div><dt>Total errors</dt><dd>{runtime?.errors ?? "—"}</dd></div>
          <div><dt>Client errors</dt><dd>{runtime?.client_errors ?? "—"}</dd></div>
          <div><dt>Maximum latency</dt><dd>{runtime ? seconds(runtime.max_duration_seconds) : "—"}</dd></div>
          <div><dt>Overall error rate</dt><dd>{runtime ? pct(runtime.error_rate) : "—"}</dd></div>
        </dl>
      </article>
      <article className="card">
        <span className="eyebrow">TRACING & CORRELATION</span><h2>Request tracing hooks</h2>
        <dl className="detail-list">
          <div><dt>Inbound header</dt><dd><code>{hooks?.request_id.header_in ?? "—"}</code></dd></div>
          <div><dt>Outbound header</dt><dd><code>{hooks?.request_id.header_out ?? "—"}</code></dd></div>
          <div><dt>Middleware</dt><dd>{hooks?.request_id.middleware ?? "—"}</dd></div>
          <div><dt>Request-ID behaviour</dt><dd>{hooks?.request_id.behavior ?? "—"}</dd></div>
        </dl>
      </article>
    </div>

    {hooks && <article className="card">
      <span className="eyebrow">PRIVACY & EXTENSIBILITY</span><h2>Operational design</h2>
      <p>{hooks.privacy}</p>
      <p><strong>Recorded metrics:</strong> {hooks.metrics.recorded.join(", ")}.</p>
      <div className="info-box">{hooks.external_apm}</div>
    </article>}

    {slos && <p className="muted small">Generated {new Date(slos.generated_at).toLocaleString()}. {slos.note}</p>}
  </section>;
}
