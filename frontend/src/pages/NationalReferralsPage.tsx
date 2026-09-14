import { useEffect, useRef, useState } from "react";
import { getNationalReferralMetrics, getNationalReferrals } from "../api/nationalReferralsApi";
import type { NationalReferralItem, NationalReferralMetrics } from "../api/nationalReferrals";

const statuses = ["", "CREATED", "SENT", "ACCEPTED", "IN_PROGRESS", "COMPLETED", "DECLINED", "CANCELLED"];
const priorities = ["", "ROUTINE", "URGENT", "EMERGENCY"];

export function NationalReferralsPage() {
  const [items, setItems] = useState<NationalReferralItem[]>([]);
  const [metrics, setMetrics] = useState<NationalReferralMetrics | null>(null);
  const [county, setCounty] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const requestRef = useRef(0);

  async function load() {
    const requestId = ++requestRef.current;
    setLoading(true); setError("");
    try {
      const [result, performance] = await Promise.all([
        getNationalReferrals({ county, status, priority, startDate, endDate }),
        getNationalReferralMetrics({ county, startDate, endDate }),
      ]);
      if (requestId !== requestRef.current) return;
      setItems(result.items); setTotal(result.total); setMetrics(performance);
    } catch (err) {
      if (requestId !== requestRef.current) return;
      setError(err instanceof Error ? err.message : "NATIONAL_REFERRAL_REQUEST_FAILED");
    } finally {
      if (requestId === requestRef.current) setLoading(false);
    }
  }

  useEffect(() => { void load(); return () => { requestRef.current += 1; }; }, []);

  return <section className="page-stack">
    <header className="page-heading">
      <div><p className="eyebrow">National care coordination</p><h1>Referral network</h1><p className="muted">Operational referral routing and network performance across active facilities. Patient identity and clinical referral content are excluded.</p></div>
      <button type="button" className="button secondary" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button>
    </header>
    <article className="card">
      <div className="filter-row">
        <label>County<input value={county} maxLength={100} placeholder="All counties" onChange={e => setCounty(e.target.value)} /></label>
        <label>Status<select value={status} onChange={e => setStatus(e.target.value)}>{statuses.map(value => <option key={value} value={value}>{value || "All statuses"}</option>)}</select></label>
        <label>Priority<select value={priority} onChange={e => setPriority(e.target.value)}>{priorities.map(value => <option key={value} value={value}>{value || "All priorities"}</option>)}</select></label>
        <label>From<input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} /></label>
        <label>To<input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} /></label>
        <button type="button" className="button filter-action" onClick={() => void load()} disabled={loading}>Apply filters</button>
      </div>
    </article>
    {error && <div className="error-banner" role="alert">{error === "PERMISSION_DENIED" ? "National referral visibility permission required." : error}</div>}
    <div className="metrics-grid">
      <article className="card metric-card"><span className="muted">Matching referrals</span><strong>{total.toLocaleString()}</strong></article>
      <article className="card metric-card"><span className="muted">Active</span><strong>{metrics?.active.toLocaleString() ?? "—"}</strong></article>
      <article className="card metric-card"><span className="muted">Completion rate</span><strong>{metrics ? `${metrics.completion_rate.toFixed(1)}%` : "—"}</strong></article>
      <article className="card metric-card"><span className="muted">Acceptance rate</span><strong>{metrics ? `${metrics.acceptance_rate.toFixed(1)}%` : "—"}</strong></article>
    </div>
    <div className="two-column-grid">
      <article className="card"><div className="card-header"><div><h2>Open referral age</h2><p className="muted">Active referrals grouped by elapsed age.</p></div></div>{metrics?.aging.map(bucket => <div className="metric-row" key={bucket.bucket}><span>{bucket.bucket}</span><strong>{bucket.count.toLocaleString()}</strong></div>) ?? <p className="muted">No performance data.</p>}</article>
      <article className="card"><div className="card-header"><div><h2>Route pressure</h2><p className="muted">Highest-volume active routes, without patient-level data.</p></div></div>{metrics?.routes.length ? <div className="table-wrap"><table><thead><tr><th>Route</th><th>Total</th><th>Active</th></tr></thead><tbody>{metrics.routes.slice(0, 10).map(route => <tr key={`${route.source_facility_id}-${route.destination_facility_id}`}><td><strong>{route.source_facility_name}</strong><div className="muted small">→ {route.destination_facility_name}</div></td><td>{route.total.toLocaleString()}</td><td>{route.active.toLocaleString()}</td></tr>)}</tbody></table></div> : <p className="muted">No route data.</p>}</article>
    </div>
    <article className="card">
      <div className="card-header"><div><h2>Referral routing queue</h2><p className="muted">Latest operational records from active source and destination facilities.</p></div></div>
      {loading ? <p className="muted">Loading referral network…</p> : items.length === 0 ? <div className="empty-state"><strong>No referral records found</strong><span>Adjust the filters or confirm active facilities have referrals.</span></div> : <div className="table-wrap"><table><thead><tr><th>Referral</th><th>From</th><th>To</th><th>Department</th><th>Priority</th><th>Status</th><th>Created</th></tr></thead><tbody>{items.map(item => <tr key={item.id}><td><strong>{item.referral_id}</strong></td><td><strong>{item.source_facility_name}</strong><div className="muted small">{item.source_facility_code} · {item.source_county || "Unspecified"}</div></td><td><strong>{item.destination_facility_name}</strong><div className="muted small">{item.destination_facility_code} · {item.destination_county || "Unspecified"}</div></td><td>{item.destination_department_name || "—"}</td><td>{item.priority}</td><td><span className="status-pill">{item.status}</span></td><td>{new Date(item.created_at).toLocaleString("en-KE")}</td></tr>)}</tbody></table></div>}
    </article>
  </section>;
}
