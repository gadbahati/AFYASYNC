import { useEffect, useState } from "react";
import { getNationalReferrals } from "../api/nationalReferralsApi";
import type { NationalReferralItem } from "../api/nationalReferrals";

const statuses = ["", "CREATED", "SENT", "ACCEPTED", "IN_PROGRESS", "COMPLETED", "DECLINED", "CANCELLED"];
const priorities = ["", "ROUTINE", "URGENT", "EMERGENCY"];

export function NationalReferralsPage() {
  const [items, setItems] = useState<NationalReferralItem[]>([]);
  const [county, setCounty] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [statusCounts, setStatusCounts] = useState<{ status: string; count: number }[]>([]);
  const [priorityCounts, setPriorityCounts] = useState<{ priority: string; count: number }[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try {
      const result = await getNationalReferrals({ county, status, priority, startDate, endDate });
      setItems(result.items); setTotal(result.total); setStatusCounts(result.status_counts); setPriorityCounts(result.priority_counts);
    } catch (err) { setError(err instanceof Error ? err.message : "NATIONAL_REFERRAL_REQUEST_FAILED"); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  return <section className="page-stack">
    <header className="page-heading">
      <div><p className="eyebrow">National care coordination</p><h1>Referral network</h1><p className="muted">Operational referral routing across active facilities. Patient identity and clinical referral content are intentionally excluded.</p></div>
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
      <article className="card metric-card"><span className="muted">Emergency</span><strong>{priorityCounts.find(item => item.priority === "EMERGENCY")?.count ?? 0}</strong></article>
      <article className="card metric-card"><span className="muted">In progress</span><strong>{statusCounts.find(item => item.status === "IN_PROGRESS")?.count ?? 0}</strong></article>
    </div>
    <article className="card">
      <div className="card-header"><div><h2>Referral routing queue</h2><p className="muted">Latest operational records from active source and destination facilities.</p></div></div>
      {loading ? <p className="muted">Loading referral network…</p> : items.length === 0 ? <div className="empty-state"><strong>No referral records found</strong><span>Adjust the filters or confirm active facilities have referrals.</span></div> : <div className="table-wrap"><table><thead><tr><th>Referral</th><th>From</th><th>To</th><th>Department</th><th>Priority</th><th>Status</th><th>Created</th></tr></thead><tbody>{items.map(item => <tr key={item.id}><td><strong>{item.referral_id}</strong></td><td><strong>{item.source_facility_name}</strong><div className="muted small">{item.source_facility_code} · {item.source_county || "Unspecified"}</div></td><td><strong>{item.destination_facility_name}</strong><div className="muted small">{item.destination_facility_code} · {item.destination_county || "Unspecified"}</div></td><td>{item.destination_department_name || "—"}</td><td>{item.priority}</td><td><span className="status-pill">{item.status}</span></td><td>{new Date(item.created_at).toLocaleString("en-KE")}</td></tr>)}</tbody></table></div>}
    </article>
  </section>;
}
