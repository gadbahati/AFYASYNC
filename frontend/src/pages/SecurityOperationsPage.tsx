import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

type ChecklistItem = { id: string; pass: boolean; detail: string };
type AccessReview = {
  window_days: number; events_scanned: number; action_counts: Record<string, number>;
  sensitive_access: Array<{ id: string; action: string; resource_type?: string | null; resource_id?: string | null; result?: string | null; user_id?: string | null; patient_id?: string | null; created_at?: string | null }>;
  generated_at: string;
};
type PrivacySummary = { portal_or_citizen_access_events: number; mutating_action_events: number; distinct_actions: number; top_actions: Record<string, number>; data_protection_note: string };
type SecurityChecklist = { checks: ChecklistItem[]; passed: number; total: number; score_pct: number };

function formatDate(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}
function shortId(value?: string | null) {
  if (!value) return "—";
  return value.length > 18 ? value.slice(0, 8) + "…" + value.slice(-6) : value;
}

export function SecurityOperationsPage() {
  const [days, setDays] = useState(7);
  const [review, setReview] = useState<AccessReview | null>(null);
  const [privacy, setPrivacy] = useState<PrivacySummary | null>(null);
  const [checklist, setChecklist] = useState<SecurityChecklist | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const results = await Promise.all([
        api.securityAccessReview(days, 100),
        api.securityPrivacySummary(30),
        api.securityChecklist(),
      ]);
      setReview(results[0]); setPrivacy(results[1]); setChecklist(results[2]);
    } catch (err: any) {
      setError(err?.message || "Security operations data could not be loaded.");
    } finally { setLoading(false); }
  }, [days]);

  useEffect(() => { void load(); }, [load]);

  const actionRows = useMemo(() => Object.entries(review?.action_counts || {}).slice(0, 12), [review]);
  const privacyActions = useMemo(() => Object.entries(privacy?.top_actions || {}).slice(0, 12), [privacy]);

  return <section className="page-stack">
    <div className="page-heading">
      <div><span className="eyebrow">SECURITY & PRIVACY OPERATIONS</span><h1>Security operations</h1><p className="muted">Review access activity, privacy operations and live security controls for the current facility.</p></div>
      <div className="row-between">
        <label className="small muted">Access window{" "}
          <select value={days} onChange={e => setDays(Number(e.target.value))}><option value={1}>24 hours</option><option value={7}>7 days</option><option value={30}>30 days</option><option value={90}>90 days</option></select>
        </label>
        <button type="button" onClick={() => void load()} disabled={loading}>{loading ? "Refreshing…" : "Refresh"}</button>
      </div>
    </div>

    {error && <div className="warning-box" role="alert">{error}</div>}

    <div className="card-grid">
      <article className="card"><span className="eyebrow">AUDIT ACTIVITY</span><strong className="stat-value">{review?.events_scanned ?? "—"}</strong><span className="muted">events scanned in the selected window</span></article>
      <article className="card"><span className="eyebrow">SENSITIVE ACCESS</span><strong className="stat-value">{review?.sensitive_access.length ?? "—"}</strong><span className="muted">patient or sensitive access events surfaced</span></article>
      <article className="card"><span className="eyebrow">PRIVACY ACCESS</span><strong className="stat-value">{privacy?.portal_or_citizen_access_events ?? "—"}</strong><span className="muted">portal/citizen access events in 30 days</span></article>
      <article className="card"><span className="eyebrow">SECURITY CHECKS</span><strong className="stat-value">{checklist ? checklist.passed + "/" + checklist.total : "—"}</strong><span className="muted">{checklist ? checklist.score_pct + "% passing" : "live configuration checks"}</span></article>
    </div>

    <div className="card-grid">
      <article className="card span-2">
        <div className="row-between"><div><span className="eyebrow">LIVE SECURITY CHECKLIST</span><h2>Control posture</h2></div><span className="status-pill">{checklist ? checklist.score_pct + "%" : "—"}</span></div>
        <div className="table-wrap"><table><thead><tr><th>Control</th><th>Status</th><th>Detail</th></tr></thead><tbody>
          {(checklist?.checks || []).map(item => <tr key={item.id}><td><strong>{item.id}</strong></td><td><span className={"status-pill" + (item.pass ? "" : " warning")}>{item.pass ? "PASS" : "CHECK"}</span></td><td>{item.detail}</td></tr>)}
        </tbody></table></div>
      </article>
      <article className="card"><span className="eyebrow">PRIVACY OPERATIONS</span><h2>30-day summary</h2>
        <dl className="detail-list"><div><dt>Mutating action events</dt><dd>{privacy?.mutating_action_events ?? "—"}</dd></div><div><dt>Distinct actions</dt><dd>{privacy?.distinct_actions ?? "—"}</dd></div></dl>
        {privacy?.data_protection_note && <div className="info-box">{privacy.data_protection_note}</div>}
      </article>
    </div>

    <div className="card-grid">
      <article className="card"><span className="eyebrow">TOP ACTIONS</span><h2>Audit distribution</h2>
        <div className="table-wrap"><table><thead><tr><th>Action</th><th>Events</th></tr></thead><tbody>{actionRows.map(([action, count]) => <tr key={action}><td>{action}</td><td><strong>{count}</strong></td></tr>)}</tbody></table></div>
      </article>
      <article className="card"><span className="eyebrow">PRIVACY ACTIONS</span><h2>Most frequent</h2>
        <div className="table-wrap"><table><thead><tr><th>Action</th><th>Events</th></tr></thead><tbody>{privacyActions.map(([action, count]) => <tr key={action}><td>{action}</td><td><strong>{count}</strong></td></tr>)}</tbody></table></div>
      </article>
    </div>

    <article className="card">
      <div className="row-between"><div><span className="eyebrow">ACCESS REVIEW</span><h2>Sensitive access events</h2><p className="muted">Facility-scoped audit records surfaced by the security review service.</p></div><span className="muted small">{review ? "Generated " + formatDate(review.generated_at) : ""}</span></div>
      <div className="table-wrap"><table><thead><tr><th>Time</th><th>Action</th><th>User</th><th>Patient</th><th>Resource</th><th>Result</th></tr></thead><tbody>
        {(review?.sensitive_access || []).map(row => <tr key={row.id}><td>{formatDate(row.created_at)}</td><td><strong>{row.action}</strong></td><td>{shortId(row.user_id)}</td><td>{shortId(row.patient_id)}</td><td>{row.resource_type ? row.resource_type + (row.resource_id ? " / " + shortId(row.resource_id) : "") : "—"}</td><td>{row.result || "—"}</td></tr>)}
      </tbody></table></div>
      {!loading && review && review.sensitive_access.length === 0 && <div className="info-box">No sensitive access events were returned for this window.</div>}
    </article>

    <div className="warning-box"><strong>Operational note:</strong> This workspace exposes audit metadata to authorised staff. It does not display patient clinical content. Use the underlying audit trail and established privacy/incident procedures for investigations.</div>
  </section>;
}
