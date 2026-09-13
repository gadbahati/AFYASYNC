import { useEffect, useState } from "react";
import { getNationalIntelligence } from "../api/national";
import type { NationalIntelligenceResponse } from "../api/types";

function defaultStart() { const d = new Date(); d.setDate(d.getDate() - 29); return d.toISOString().slice(0, 10); }

const severityClass = (severity: string) => `status-pill intelligence-${severity.toLowerCase()}`;

export function NationalIntelligencePage() {
  const [data, setData] = useState<NationalIntelligenceResponse | null>(null);
  const [start, setStart] = useState(defaultStart);
  const [end, setEnd] = useState(() => new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true); setError(null);
    getNationalIntelligence(start, end).then(setData).catch((e: unknown) => setError(e instanceof Error ? e.message : "NATIONAL_INTELLIGENCE_LOAD_FAILED")).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  return <section className="page-stack">
    <header className="page-heading"><div><p className="eyebrow">AfyaSync National Health Intelligence</p><h1>National intelligence centre</h1><p className="muted">Explainable operational signals derived from live platform data. This view contains aggregated indicators, not patient-level clinical records.</p></div><button type="button" className="button secondary" onClick={load} disabled={loading}>Refresh intelligence</button></header>
    <article className="card"><div className="form-grid"><label>From<input type="date" value={start} onChange={e => setStart(e.target.value)} /></label><label>To<input type="date" value={end} onChange={e => setEnd(e.target.value)} /></label><div className="form-actions"><button type="button" className="button" onClick={load} disabled={loading}>Analyse period</button></div></div></article>
    {error && <div className="error">{error === "PERMISSION_DENIED" ? "National reporting permission required." : error}</div>}
    {loading && <p>Generating intelligence…</p>}
    {data && <>
      <div className="metric-grid"><article className="card metric-card"><p className="muted small">Action signals</p><h2>{data.alerts.length}</h2></article><article className="card metric-card"><p className="muted small">Facilities requiring review</p><h2>{data.facility_signals.length}</h2></article><article className="card metric-card"><p className="muted small">Critical / high alerts</p><h2>{data.alerts.filter(a => a.severity === "CRITICAL" || a.severity === "HIGH").length}</h2></article><article className="card metric-card"><p className="muted small">Generated</p><h2>{new Date(data.generated_at).toLocaleTimeString("en-KE", { hour: "2-digit", minute: "2-digit" })}</h2></article></div>
      <article className="card"><div className="section-heading"><div><h2>National action signals</h2><p className="muted">Signals are rule-based, explainable and linked to a recommended operational response. They do not make autonomous clinical decisions.</p></div></div>{data.alerts.length ? <div className="stack-list">{data.alerts.map(alert => <div className="notice intelligence-alert" key={alert.code}><div className="row-between"><div><strong>{alert.title}</strong><p className="muted small">{alert.category.replaceAll("_", " ")}</p></div><span className={severityClass(alert.severity)}>{alert.severity}</span></div><p>{alert.summary}</p><p className="small"><strong>{alert.value.toLocaleString()} {alert.unit}</strong></p><p className="muted small"><strong>Recommended action:</strong> {alert.recommendation}</p></div>)}</div> : <div className="empty-state"><strong>No active intelligence signals</strong><p className="muted">No non-zero action conditions were detected in the current platform snapshot.</p></div>}</article>
      <article className="card"><div className="section-heading"><div><h2>Facility review queue</h2><p className="muted">Explainable financial and operational signals ranked by review score. A score is a prioritisation aid, not a clinical quality judgement.</p></div></div>{data.facility_signals.length ? <div className="table-wrap"><table><thead><tr><th>Facility</th><th>County</th><th>Score</th><th>Severity</th><th>Signals</th></tr></thead><tbody>{data.facility_signals.map(row => <tr key={row.facility_id}><td><strong>{row.facility_name}</strong><br /><small>{row.facility_code}</small></td><td>{row.county || "—"}</td><td><strong>{row.score}</strong>/100</td><td><span className={severityClass(row.severity)}>{row.severity}</span></td><td>{row.signals.join("; ")}</td></tr>)}</tbody></table></div> : <div className="empty-state"><strong>No facilities require review</strong><p className="muted">The selected period has no detected facility-level review signals.</p></div>}</article>
    </>}
  </section>;
}
