import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api/client";
import type { FacilityOperationsReport } from "../api/types";

const iso = (d: Date) => d.toISOString().slice(0, 10);
const money = (v: string | number) => `KES ${Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function ReportsPage() {
  const today = new Date();
  const [start, setStart] = useState(iso(new Date(today.getFullYear(), today.getMonth(), 1)));
  const [end, setEnd] = useState(iso(today));
  const [report, setReport] = useState<FacilityOperationsReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const load = async () => { setLoading(true); setError(null); try { setReport(await api.facilityOperationsReport(start, end)); } catch (e) { setError(e instanceof ApiError ? e.code : "REPORT_FAILED"); } finally { setLoading(false); } };
  useEffect(() => { void load(); }, []);
  const monthLabel = useMemo(() => report ? new Date(`${report.start_date}T00:00:00`).toLocaleDateString(undefined, { month: "long", year: "numeric" }) : "Selected period", [report]);
  return <section className="page-stack">
    <header className="page-heading"><div><p className="eyebrow">Facility operations & reporting</p><h1>Daily & monthly reports</h1><p className="muted">Live database reports for patients, clinical care, diagnoses, prescriptions, admissions, referrals, billing and medicine movements.</p></div><div className="form-actions"><button type="button" className="button secondary" onClick={() => window.print()}>Print / save PDF</button></div></header>
    <article className="card no-print"><div className="form-grid"><label>Start date<input type="date" value={start} onChange={e => setStart(e.target.value)} /></label><label>End date<input type="date" value={end} onChange={e => setEnd(e.target.value)} /></label><div className="actions"><button type="button" disabled={loading || !start || !end} onClick={() => void load()}>{loading ? "Generating…" : "Generate report"}</button></div></div></article>
    {error && <div className="error">{error}</div>}{loading && <div className="card">Generating report from the live facility database…</div>}
    {report && !loading && <>
      <div className="card-grid"><Metric label="Patients registered" value={report.patients.toLocaleString()} /><Metric label="Encounters" value={report.encounters.toLocaleString()} /><Metric label="Diagnoses" value={report.diagnoses.toLocaleString()} /><Metric label="Prescriptions" value={report.prescriptions.toLocaleString()} /><Metric label="Admissions" value={report.admissions.toLocaleString()} /><Metric label="Referrals" value={report.referrals.toLocaleString()} /><Metric label="Billed" value={money(report.invoices_total)} /><Metric label="Confirmed payments" value={money(report.confirmed_payments)} /><Metric label="Stock received" value={Number(report.stock_received_quantity).toLocaleString()} /><Metric label="Stock dispensed" value={Number(report.stock_dispensed_quantity).toLocaleString()} /></div>
      <article className="card"><div className="row-between"><div><p className="eyebrow">Clinical intelligence</p><h2>Most recorded diagnoses</h2></div><span className="status-pill">{monthLabel}</span></div><div className="table-wrap"><table><thead><tr><th>Disease / diagnosis</th><th>Recorded</th></tr></thead><tbody>{report.top_diagnoses.map(d => <tr key={d.diagnosis}><td>{d.diagnosis}</td><td>{d.count}</td></tr>)}{report.top_diagnoses.length === 0 && <tr><td colSpan={2} className="muted">No diagnoses recorded in this period.</td></tr>}</tbody></table></div></article>
      <article className="card"><div className="row-between"><div><p className="eyebrow">Operational ledger</p><h2>Daily activity</h2></div><span className="muted">{report.start_date} → {report.end_date}</span></div><div className="table-wrap"><table><thead><tr><th>Date</th><th>Patients</th><th>Encounters</th><th>Diagnoses</th><th>Rx</th><th>Admissions</th><th>Referrals</th><th>Billed</th><th>Paid</th><th>Stock in</th><th>Dispensed</th></tr></thead><tbody>{report.daily.map(d => <tr key={d.date}><td>{d.date}</td><td>{d.patients}</td><td>{d.encounters}</td><td>{d.diagnoses}</td><td>{d.prescriptions}</td><td>{d.admissions}</td><td>{d.referrals}</td><td>{money(d.invoices)}</td><td>{money(d.payments)}</td><td>{d.stock_received_quantity}</td><td>{d.stock_dispensed_quantity}</td></tr>)}</tbody></table></div></article>
    </>}
  </section>;
}
function Metric({ label, value }: { label: string; value: string }) { return <article className="card"><p className="eyebrow">{label}</p><strong style={{ fontSize: "1.6rem" }}>{value}</strong></article>; }
