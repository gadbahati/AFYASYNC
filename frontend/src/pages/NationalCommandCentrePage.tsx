import { useEffect, useMemo, useState } from "react";
import { getNationalReport } from "../api/national";
import type { NationalReport } from "../api/types";

function money(value: string) {
  return `KES ${Number(value).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function defaultStart() {
  const d = new Date();
  d.setDate(d.getDate() - 29);
  return d.toISOString().slice(0, 10);
}

export function NationalCommandCentrePage() {
  const [report, setReport] = useState<NationalReport | null>(null);
  const [start, setStart] = useState(defaultStart);
  const [end, setEnd] = useState(() => new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    getNationalReport(start, end)
      .then(setReport)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "NATIONAL_REPORT_LOAD_FAILED"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const approvalRate = useMemo(() => {
    if (!report || Number(report.claims_amount) <= 0) return "0.0%";
    return `${((Number(report.claims_approved) / Number(report.claims_amount)) * 100).toFixed(1)}%`;
  }, [report]);

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">AfyaSync National Health Platform</p>
          <h1>National command centre</h1>
          <p className="muted">Cross-facility operational and financing intelligence. Patient-level clinical records remain outside this view.</p>
        </div>
        <button type="button" className="button secondary" onClick={load} disabled={loading}>Refresh</button>
      </header>

      <article className="card">
        <div className="form-grid">
          <label>From<input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></label>
          <label>To<input type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></label>
          <div className="form-actions"><button type="button" className="button" onClick={load} disabled={loading}>Apply period</button></div>
        </div>
      </article>

      {error && <div className="error">{error === "PERMISSION_DENIED" ? "National reporting permission required." : error}</div>}
      {loading && <p>Loading national reporting…</p>}

      {report && (
        <>
          <div className="metric-grid">
            <article className="card metric-card"><p className="muted small">Active facilities</p><h2>{report.active_facilities.toLocaleString()}</h2></article>
            <article className="card metric-card"><p className="muted small">Registered patients</p><h2>{report.registered_patients.toLocaleString()}</h2></article>
            <article className="card metric-card"><p className="muted small">Encounters</p><h2>{report.encounters.toLocaleString()}</h2></article>
            <article className="card metric-card"><p className="muted small">Confirmed payments</p><h2>{money(report.confirmed_payments)}</h2></article>
          </div>

          <div className="metric-grid">
            <article className="card metric-card"><p className="muted small">Invoices</p><h2>{money(report.invoices_total)}</h2></article>
            <article className="card metric-card"><p className="muted small">Claims submitted</p><h2>{report.claims.toLocaleString()}</h2></article>
            <article className="card metric-card"><p className="muted small">Claims approved</p><h2>{money(report.claims_approved)}</h2></article>
            <article className="card metric-card"><p className="muted small">Claims receivable</p><h2>{money(report.claims_receivable)}</h2></article>
          </div>

          <div className="two-col">
            <article className="card">
              <h2>Claim performance</h2>
              <p className="muted">Approval rate by claim value: {approvalRate}</p>
              <div className="table-wrap"><table><thead><tr><th>Status</th><th>Claims</th><th>Amount</th><th>Approved</th><th>Paid</th></tr></thead><tbody>
                {report.claim_statuses.map((row) => <tr key={row.status}><td>{row.status}</td><td>{row.count}</td><td>{money(row.amount)}</td><td>{money(row.approved_amount)}</td><td>{money(row.paid_amount)}</td></tr>)}
                {!report.claim_statuses.length && <tr><td colSpan={5} className="muted">No claims in this period</td></tr>}
              </tbody></table></div>
            </article>
            <article className="card">
              <h2>Payer performance</h2>
              <div className="table-wrap"><table><thead><tr><th>Payer</th><th>Claims</th><th>Billed</th><th>Paid</th><th>Receivable</th></tr></thead><tbody>
                {report.payer_claims.map((row) => <tr key={row.payer_id}><td><strong>{row.payer_name}</strong><br /><small>{row.payer_code}</small></td><td>{row.claims}</td><td>{money(row.amount)}</td><td>{money(row.paid_amount)}</td><td>{money(row.receivable)}</td></tr>)}
                {!report.payer_claims.length && <tr><td colSpan={5} className="muted">No payer claims in this period</td></tr>}
              </tbody></table></div>
            </article>
          </div>

          <article className="card">
            <div className="row-between"><div><h2>Facility performance</h2><p className="muted">Active facilities with real activity in the selected reporting period.</p></div><span className="status-pill">{report.facilities.length} ACTIVE</span></div>
            <div className="table-wrap"><table><thead><tr><th>Facility</th><th>County</th><th>Encounters</th><th>Billed</th><th>Payments</th><th>Claims</th><th>Receivable</th></tr></thead><tbody>
              {report.facilities.map((row) => <tr key={row.facility_id}><td><strong>{row.facility_name}</strong><br /><small>{row.facility_code}</small></td><td>{row.county || "—"}</td><td>{row.encounters.toLocaleString()}</td><td>{money(row.billed)}</td><td>{money(row.confirmed_payments)}</td><td>{row.claims.toLocaleString()}</td><td>{money(row.claims_receivable)}</td></tr>)}
              {!report.facilities.length && <tr><td colSpan={7} className="muted">No active facilities found</td></tr>}
            </tbody></table></div>
          </article>
        </>
      )}
    </section>
  );
}
