import { useCallback, useEffect, useState } from "react";
import { getNationalIntelligence } from "../api/nationalIntelligenceApi";
import type { NationalIntelligenceResponse } from "../api/nationalIntelligence";

function formatDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function defaultStart() {
  const date = new Date();
  date.setDate(date.getDate() - 29);
  return formatDate(date);
}

const severityClass = (severity: string) => `status-pill intelligence-${severity.toLowerCase()}`;
const money = (value: number) => new Intl.NumberFormat("en-KE", { style: "currency", currency: "KES", maximumFractionDigits: 0 }).format(value);

export function NationalIntelligenceCentrePage() {
  const [data, setData] = useState<NationalIntelligenceResponse | null>(null);
  const [start, setStart] = useState(defaultStart);
  const [end, setEnd] = useState(() => formatDate(new Date()));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    if (start > end) {
      setError("INVALID_REPORT_DATE_RANGE");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await getNationalIntelligence(start, end, signal);
      if (!signal?.aborted) setData(result);
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      if (!signal?.aborted) setError(e instanceof Error ? e.message : "NATIONAL_INTELLIGENCE_LOAD_FAILED");
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [start, end]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, []);

  const validationError = start > end ? "From date cannot be after the To date." : null;

  return <section className="page-stack">
    <header className="page-heading">
      <div>
        <p className="eyebrow">AfyaSync National Health Intelligence</p>
        <h1>National intelligence centre</h1>
        <p className="muted">Explainable operational signals, period-over-period trends and county intelligence derived from live platform data. No patient-level records are exposed here.</p>
      </div>
      <button type="button" className="button secondary" onClick={() => void load()} disabled={loading || Boolean(validationError)}>Refresh intelligence</button>
    </header>

    <article className="card">
      <div className="form-grid">
        <label>From<input type="date" value={start} max={end} onChange={e => setStart(e.target.value)} /></label>
        <label>To<input type="date" value={end} min={start} onChange={e => setEnd(e.target.value)} /></label>
        <div className="form-actions"><button type="button" className="button" onClick={() => void load()} disabled={loading || Boolean(validationError)}>Analyse period</button></div>
      </div>
      {validationError && <p className="error" role="alert">{validationError}</p>}
    </article>

    {error && <div className="error" role="alert">{error === "PERMISSION_DENIED" ? "National reporting permission required." : error === "INVALID_REPORT_DATE_RANGE" ? "The selected date range is invalid." : error}</div>}
    {loading && <p aria-live="polite">Generating intelligence…</p>}

    {data && !loading && <>
      <div className="metric-grid">
        <article className="card metric-card"><p className="muted small">Action signals</p><h2>{data.alerts.length}</h2></article>
        <article className="card metric-card"><p className="muted small">Facilities requiring review</p><h2>{data.facility_signals.length}</h2></article>
        <article className="card metric-card"><p className="muted small">Critical / high alerts</p><h2>{data.alerts.filter(a => a.severity === "CRITICAL" || a.severity === "HIGH").length}</h2></article>
        <article className="card metric-card"><p className="muted small">Counties monitored</p><h2>{data.counties.length}</h2></article>
      </div>

      <article className="card">
        <div className="section-heading"><div><h2>National trend watch</h2><p className="muted">Current period compared with the immediately preceding period of the same length: {data.comparison_start_date} to {data.comparison_end_date}.</p></div></div>
        <div className="report-grid">{data.trends.map(trend => <div className="report-card card" key={trend.metric}>
          <p className="muted small">{trend.label}</p>
          <div className="row-between"><h2>{trend.metric === "encounters" || trend.metric === "claims" ? trend.current.toLocaleString() : money(trend.current)}</h2><span className={trend.direction === "UP" ? "status-pill status-warning" : trend.direction === "DOWN" ? "status-pill status-success" : "status-pill"}>{trend.change_percent === null ? (trend.previous === 0 && trend.current > 0 ? "New" : "—") : `${trend.change_percent > 0 ? "+" : ""}${trend.change_percent}%`}</span></div>
          <p className="muted small">Previous: {trend.metric === "encounters" || trend.metric === "claims" ? trend.previous.toLocaleString() : money(trend.previous)}</p>
          <p className="small">{trend.interpretation}</p>
        </div>)}</div>
      </article>

      <article className="card">
        <div className="section-heading"><div><h2>National action signals</h2><p className="muted">Rule-based and explainable signals linked to recommended operational responses. They do not make autonomous clinical decisions.</p></div></div>
        {data.alerts.length ? <div className="stack-list">{data.alerts.map(alert => <div className="notice intelligence-alert" key={alert.code}>
          <div className="row-between"><div><strong>{alert.title}</strong><p className="muted small">{alert.category.replaceAll("_", " ")}</p></div><span className={severityClass(alert.severity)}>{alert.severity}</span></div>
          <p>{alert.summary}</p><p className="small"><strong>{alert.value.toLocaleString()} {alert.unit}</strong></p><p className="muted small"><strong>Recommended action:</strong> {alert.recommendation}</p>
        </div>)}</div> : <div className="empty-state"><strong>No active intelligence signals</strong><p className="muted">No non-zero action conditions were detected in the current platform snapshot.</p></div>}
      </article>

      <article className="card">
        <div className="section-heading"><div><h2>County intelligence</h2><p className="muted">Aggregated operational and financing pressure by county. Review scores are prioritisation aids, not clinical quality judgements.</p></div></div>
        {data.counties.length ? <div className="table-wrap"><table><thead><tr><th>County</th><th>Facilities</th><th>Review</th><th>Encounters</th><th>Billed</th><th>Payments</th><th>Claims receivable</th><th>Highest score</th></tr></thead><tbody>{data.counties.map(row => <tr key={row.county}><td><strong>{row.county}</strong></td><td>{row.facilities}</td><td>{row.facilities_requiring_review}</td><td>{row.encounters.toLocaleString()}</td><td>{money(row.billed)}</td><td>{money(row.confirmed_payments)}</td><td>{money(row.claims_receivable)}</td><td>{row.highest_review_score ? <span className={severityClass(row.highest_review_score >= 70 ? "CRITICAL" : row.highest_review_score >= 45 ? "HIGH" : "MEDIUM")}>{row.highest_review_score}</span> : "—"}</td></tr>)}</tbody></table></div> : <div className="empty-state"><strong>No county activity</strong><p className="muted">No active facilities returned for the selected period.</p></div>}
      </article>

      <article className="card">
        <div className="section-heading"><div><h2>Facility review queue</h2><p className="muted">Explainable financial and operational signals ranked by review score. A score is a prioritisation aid, not a clinical quality judgement.</p></div></div>
        {data.facility_signals.length ? <div className="table-wrap"><table><thead><tr><th>Facility</th><th>County</th><th>Score</th><th>Severity</th><th>Signals</th></tr></thead><tbody>{data.facility_signals.map(row => <tr key={row.facility_id}><td><strong>{row.facility_name}</strong><br /><small>{row.facility_code}</small></td><td>{row.county || "—"}</td><td><strong>{row.score}</strong>/100</td><td><span className={severityClass(row.severity)}>{row.severity}</span></td><td>{row.signals.join("; ")}</td></tr>)}</tbody></table></div> : <div className="empty-state"><strong>No facilities require review</strong><p className="muted">The selected period has no detected facility-level review signals.</p></div>}
      </article>
    </>}
  </section>;
}
