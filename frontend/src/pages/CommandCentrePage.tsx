import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";

type Metric = { key: string; label: string; value: number | string; unit?: string | null; tone: string };
type CommandCentre = {
  facility_id: string;
  generated_at: string;
  metrics: Metric[];
  claim_pipeline: Record<string, number>;
  coverage_mix: Record<string, number>;
  alerts: string[];
};
type FraudSignal = { code: string; severity: string; title: string; detail: string; resource_type?: string | null; resource_id?: string | null };
type FraudRadar = { facility_id: string; scanned_at: string; signals: FraudSignal[]; summary: string };

export function CommandCentrePage() {
  const [centre, setCentre] = useState<CommandCentre | null>(null);
  const [fraud, setFraud] = useState<FraudRadar | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    setError(null);
    Promise.all([api.commandCentre(), api.fraudRadar()])
      .then(([c, f]) => {
        setCentre(c);
        setFraud(f);
      })
      .catch((e) => setError(e instanceof ApiError ? e.code : "INSIGHT_LOAD_FAILED"))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">AfyaSync Insight</p>
          <h1>Command centre</h1>
          <p className="muted">Facility pulse: encounters, claims pipeline, coverage mix, stock risk and fraud radar — the view SHA does not give hospital managers.</p>
        </div>
        <button type="button" className="button secondary" onClick={load}>Refresh</button>
      </header>
      {error && <div className="error">{error}</div>}
      {loading && <p>Loading command centre…</p>}
      {centre && (
        <>
          <div className="metric-grid">
            {centre.metrics.map((m) => (
              <article className={`card metric-card tone-${m.tone}`} key={m.key}>
                <p className="muted small">{m.label}</p>
                <h2>{m.value}{m.unit ? ` ${m.unit}` : ""}</h2>
              </article>
            ))}
          </div>
          <article className="card">
            <h2>Alerts</h2>
            <ul>{centre.alerts.map((a) => <li key={a}>{a}</li>)}</ul>
            <p className="muted small">Generated {new Date(centre.generated_at).toLocaleString()}</p>
          </article>
          <div className="two-col">
            <article className="card">
              <h2>Claims pipeline</h2>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Status</th><th>Count</th></tr></thead>
                  <tbody>
                    {Object.entries(centre.claim_pipeline).map(([k, v]) => (
                      <tr key={k}><td>{k}</td><td>{v}</td></tr>
                    ))}
                    {Object.keys(centre.claim_pipeline).length === 0 && <tr><td colSpan={2} className="muted">No claims yet</td></tr>}
                  </tbody>
                </table>
              </div>
            </article>
            <article className="card">
              <h2>Coverage mix (encounters)</h2>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Mode</th><th>Count</th></tr></thead>
                  <tbody>
                    {Object.entries(centre.coverage_mix).map(([k, v]) => (
                      <tr key={k}><td>{k}</td><td>{v}</td></tr>
                    ))}
                    {Object.keys(centre.coverage_mix).length === 0 && <tr><td colSpan={2} className="muted">No encounters yet</td></tr>}
                  </tbody>
                </table>
              </div>
            </article>
          </div>
        </>
      )}
      {fraud && (
        <article className="card">
          <div className="row-between">
            <div>
              <h2>Fraud radar</h2>
              <p className="muted">{fraud.summary}</p>
            </div>
            <span className="status-pill">SCANNED</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Severity</th><th>Signal</th><th>Detail</th></tr></thead>
              <tbody>
                {fraud.signals.map((s) => (
                  <tr key={s.code + (s.resource_id || "")}>
                    <td><span className={s.severity === "HIGH" ? "badge" : "status-pill"}>{s.severity}</span></td>
                    <td><strong>{s.title}</strong><br /><small>{s.code}</small></td>
                    <td>{s.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      )}
    </section>
  );
}
