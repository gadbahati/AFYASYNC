import { useEffect, useMemo, useState } from "react";
import { getNationalReport } from "../api/national";
import type { NationalReport } from "../api/types";

function money(value: string) {
  return `KES ${Number(value).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function defaultStart() { const d = new Date(); d.setDate(d.getDate() - 29); return d.toISOString().slice(0, 10); }

export function NationalCommandCentrePage() {
  const [report, setReport] = useState<NationalReport | null>(null);
  const [start, setStart] = useState(defaultStart);
  const [end, setEnd] = useState(() => new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = () => { setLoading(true); setError(null); getNationalReport(start, end).then(setReport).catch((e: unknown) => setError(e instanceof Error ? e.message : "NATIONAL_REPORT_LOAD_FAILED")).finally(() => setLoading(false)); };
  useEffect(() => { load(); }, []);
  const approvalRate = useMemo(() => !report || Number(report.claims_amount) <= 0 ? "0.0%" : `${((Number(report.claims_approved) / Number(report.claims_amount)) * 100).toFixed(1)}%`, [report]);
  const ops = report?.operations;
  const alerts = useMemo(() => {
    if (!ops) return [] as Array<{ label: string; value: number; detail: string }>;
    return [
      { label: "Integration failures", value: ops.integration_failed, detail: "Failed transactions require operational review." },
      { label: "Integration retries", value: ops.integration_retrying, detail: "Transactions are awaiting another delivery attempt." },
      { label: "Rejected claims", value: ops.rejected_claims, detail: "Claims require payer-response review or rework." },
      { label: "Low-stock items", value: ops.low_stock_items, detail: "Inventory items are at or below their configured minimum." },
      { label: "Open encounters", value: ops.open_encounters, detail: "Encounters remain clinically open." },
      { label: "Open invoices", value: ops.open_invoices, detail: "Invoices remain open or partially settled." },
    ].filter(item => item.value > 0);
  }, [ops]);
  const facilityTriage = useMemo(() => {
    if (!report) return [];
    return [...report.facilities].sort((a, b) => {
      const workloadA = a.encounters + a.claims;
      const workloadB = b.encounters + b.claims;
      return workloadB - workloadA || Number(b.claims_receivable) - Number(a.claims_receivable);
    });
  }, [report]);
  const servicePressure = useMemo(() => {
    if (!report || !ops || report.active_facilities <= 0) return null;
    return {
      encountersPerFacility: ops.encounters_24h / report.active_facilities,
      openEncountersPerFacility: ops.open_encounters / report.active_facilities,
      lowStockPerFacility: ops.low_stock_items / report.active_facilities,
      pendingPrescriptionsPerFacility: ops.pending_prescriptions / report.active_facilities,
    };
  }, [report, ops]);

  return <section className="page-stack">
    <header className="page-heading"><div><p className="eyebrow">AfyaSync National Health Platform</p><h1>National command centre</h1><p className="muted">Cross-facility operational, clinical-flow and financing intelligence. Patient-level clinical records remain outside this view.</p></div><button type="button" className="button secondary" onClick={load} disabled={loading}>Refresh</button></header>
    <article className="card"><div className="form-grid"><label>From<input type="date" value={start} onChange={e => setStart(e.target.value)} /></label><label>To<input type="date" value={end} onChange={e => setEnd(e.target.value)} /></label><div className="form-actions"><button type="button" className="button" onClick={load} disabled={loading}>Apply period</button></div></div></article>
    {error && <div className="error">{error === "PERMISSION_DENIED" ? "National reporting permission required." : error}</div>}{loading && <p>Loading national reporting…</p>}
    {report && <>
      <div className="metric-grid">{[["Active facilities", report.active_facilities], ["Registered patients", report.registered_patients], ["Encounters", report.encounters], ["Confirmed payments", money(report.confirmed_payments)]].map(([label, value]) => <article className="card metric-card" key={String(label)}><p className="muted small">{label}</p><h2>{typeof value === "number" ? value.toLocaleString() : value}</h2></article>)}</div>

      {ops && <article className="card"><div className="section-heading"><div><h2>Live operational picture</h2><p className="muted">Current workload across active facilities, independent of the selected financial period.</p></div></div><div className="metric-grid">{[["Open encounters", ops.open_encounters], ["Encounters (24h)", ops.encounters_24h], ["Open invoices", ops.open_invoices], ["Pending prescriptions", ops.pending_prescriptions], ["Low-stock items", ops.low_stock_items], ["Rejected claims", ops.rejected_claims], ["Integration pending", ops.integration_pending], ["Integration retrying", ops.integration_retrying], ["Integration failed", ops.integration_failed]].map(([label, value]) => <article className="card metric-card" key={String(label)}><p className="muted small">{label}</p><h2>{Number(value).toLocaleString()}</h2></article>)}</div></article>}

      <div className="two-col">
        <article className="card"><div className="section-heading"><div><h2>National alerts</h2><p className="muted">Action queue generated from current platform state. Zero-count conditions stay out of the queue.</p></div><span className="status-pill">{alerts.length} OPEN</span></div>{alerts.length ? <div className="stack-list">{alerts.map(alert => <div className="notice" key={alert.label}><div className="row-between"><strong>{alert.label}</strong><strong>{alert.value.toLocaleString()}</strong></div><p className="muted small">{alert.detail}</p></div>)}</div> : <div className="empty-state"><strong>No active national alerts</strong><p className="muted">The current operational snapshot has no non-zero alert conditions.</p></div>}</article>
        <article className="card"><div className="section-heading"><div><h2>Service pressure</h2><p className="muted">Current workload normalized by active facility count.</p></div></div>{servicePressure ? <div className="metric-grid">{[["Encounters / facility (24h)", servicePressure.encountersPerFacility], ["Open encounters / facility", servicePressure.openEncountersPerFacility], ["Low-stock / facility", servicePressure.lowStockPerFacility], ["Pending prescriptions / facility", servicePressure.pendingPrescriptionsPerFacility]].map(([label, value]) => <article className="card metric-card" key={String(label)}><p className="muted small">{label}</p><h2>{Number(value).toFixed(1)}</h2></article>)}</div> : <p className="muted">No active facilities are available for normalization.</p>}</article>
      </div>

      <div className="metric-grid"><article className="card metric-card"><p className="muted small">Invoices</p><h2>{money(report.invoices_total)}</h2></article><article className="card metric-card"><p className="muted small">Claims</p><h2>{report.claims.toLocaleString()}</h2></article><article className="card metric-card"><p className="muted small">Claims approved</p><h2>{money(report.claims_approved)}</h2></article><article className="card metric-card"><p className="muted small">Claims receivable</p><h2>{money(report.claims_receivable)}</h2></article></div>
      <div className="two-col"><article className="card"><h2>Claim performance</h2><p className="muted">Approval rate by claim value: {approvalRate}</p><div className="table-wrap"><table><thead><tr><th>Status</th><th>Claims</th><th>Amount</th><th>Approved</th><th>Paid</th></tr></thead><tbody>{report.claim_statuses.map(row => <tr key={row.status}><td>{row.status}</td><td>{row.count}</td><td>{money(row.amount)}</td><td>{money(row.approved_amount)}</td><td>{money(row.paid_amount)}</td></tr>)}{!report.claim_statuses.length && <tr><td colSpan={5} className="muted">No claims in this period</td></tr>}</tbody></table></div></article><article className="card"><h2>Payer performance</h2><div className="table-wrap"><table><thead><tr><th>Payer</th><th>Claims</th><th>Billed</th><th>Paid</th><th>Receivable</th></tr></thead><tbody>{report.payer_claims.map(row => <tr key={row.payer_id}><td><strong>{row.payer_name}</strong><br /><small>{row.payer_code}</small></td><td>{row.claims}</td><td>{money(row.amount)}</td><td>{money(row.paid_amount)}</td><td>{money(row.receivable)}</td></tr>)}{!report.payer_claims.length && <tr><td colSpan={5} className="muted">No payer claims in this period</td></tr>}</tbody></table></div></article></div>
      <article className="card"><div className="row-between"><div><h2>Facility triage</h2><p className="muted">Facilities ranked by real encounter and claims workload, with receivables used as a secondary operational signal.</p></div><span className="status-pill">{facilityTriage.length} ACTIVE</span></div><div className="table-wrap"><table><thead><tr><th>Facility</th><th>County</th><th>Encounters</th><th>Billed</th><th>Payments</th><th>Claims</th><th>Receivable</th></tr></thead><tbody>{facilityTriage.map(row => <tr key={row.facility_id}><td><strong>{row.facility_name}</strong><br /><small>{row.facility_code}</small></td><td>{row.county || "—"}</td><td>{row.encounters.toLocaleString()}</td><td>{money(row.billed)}</td><td>{money(row.confirmed_payments)}</td><td>{row.claims.toLocaleString()}</td><td>{money(row.claims_receivable)}</td></tr>)}{!facilityTriage.length && <tr><td colSpan={7} className="muted">No active facilities found</td></tr>}</tbody></table></div></article>
    </>}
  </section>;
}
