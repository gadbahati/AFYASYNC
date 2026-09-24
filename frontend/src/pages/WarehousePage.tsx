import { useCallback, useEffect, useState } from "react";
import { api, downloadWarehouseCsv } from "../api/client";

type Fact = {
  active_facilities: number;
  active_staff: number;
  encounters: number;
  claims: number;
  notifiable_events: number;
  ambulance_requests: number;
  teleconsult_requests: number;
};

type CountyRow = {
  county: string;
  active_facilities: number;
  encounters_all_time: number;
  claims_in_window: number;
  window_days: number;
};

export function WarehousePage() {
  const [days, setDays] = useState(30);
  const [facts, setFacts] = useState<Fact | null>(null);
  const [claims, setClaims] = useState<Record<string, number>>({});
  const [conditions, setConditions] = useState<Record<string, number>>({});
  const [rows, setRows] = useState<CountyRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [summary, county] = await Promise.all([
        api.warehouseFacts(days),
        api.warehouseCountyFacts(days),
      ]);
      setFacts(summary.facts || null);
      setClaims(summary.claim_status || {});
      setConditions(summary.notifiable_by_condition || {});
      setRows(county.rows || []);
    } catch (e: any) { setError(e?.message || "Warehouse data could not be loaded."); }
    finally { setLoading(false); }
  }, [days]);

  useEffect(() => { void load(); }, [load]);

  const exportCsv = async () => {
    setExporting(true);
    try {
      const csv = await downloadWarehouseCsv(days);
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      const a = document.createElement("a"); a.href = url; a.download = "afyasync_county_facts.csv"; a.click(); URL.revokeObjectURL(url);
    } catch (e: any) { setError(e?.message || "CSV export failed."); }
    finally { setExporting(false); }
  };

  return <section className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">PHASE 29 • ANALYTICS WAREHOUSE</span><h1>National data warehouse</h1><p className="muted">De-identified aggregate facts for operational reporting and controlled county exports.</p></div><button onClick={() => void load()} disabled={loading}>{loading ? "Refreshing…" : "Refresh"}</button></div>
    {error && <div className="warning-box">{error}</div>}
    <div className="card"><div className="row-between"><div><span className="eyebrow">TIME WINDOW</span><h2>Reporting period</h2></div><button onClick={() => void exportCsv()} disabled={exporting}>{exporting ? "Preparing…" : "Export county CSV"}</button></div><select value={days} onChange={e => setDays(Number(e.target.value))}><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={180}>Last 180 days</option><option value={365}>Last 365 days</option></select></div>
    <div className="stat-grid">
      {[
        ["ACTIVE FACILITIES", facts?.active_facilities],["ACTIVE STAFF",facts?.active_staff],["ENCOUNTERS",facts?.encounters],["CLAIMS",facts?.claims],["NOTIFIABLE EVENTS",facts?.notifiable_events],["AMBULANCE REQUESTS",facts?.ambulance_requests],["TELECONSULTS",facts?.teleconsult_requests]
      ].map(([label,value]) => <div className="stat-card" key={label as string}><span className="eyebrow">{label}</span><strong>{value ?? "—"}</strong><span className="muted">{days}-day warehouse view</span></div>)}
    </div>
    <div className="card-grid">
      <article className="card"><span className="eyebrow">CLAIM STATUS</span><h2>Claims by status</h2>{Object.entries(claims).length ? <div className="list-stack">{Object.entries(claims).map(([k,v]) => <div className="row-between" key={k}><span>{k}</span><strong>{v}</strong></div>)}</div> : <p className="muted">No claim status rows in this window.</p>}</article>
      <article className="card"><span className="eyebrow">SURVEILLANCE</span><h2>Notifiable conditions</h2>{Object.entries(conditions).length ? <div className="list-stack">{Object.entries(conditions).map(([k,v]) => <div className="row-between" key={k}><span>{k}</span><strong>{v}</strong></div>)}</div> : <p className="muted">No notifiable-event rows in this window.</p>}</article>
    </div>
    <div className="card"><span className="eyebrow">COUNTY FACT TABLE</span><h2>Operational county rows</h2><div className="table-wrap"><table><thead><tr><th>County</th><th>Active facilities</th><th>Encounters</th><th>Claims</th><th>Window</th></tr></thead><tbody>{rows.map(r => <tr key={r.county}><td><strong>{r.county}</strong></td><td>{r.active_facilities}</td><td>{r.encounters_all_time}</td><td>{r.claims_in_window}</td><td>{r.window_days} days</td></tr>)}</tbody></table></div></div>
    <div className="card"><span className="eyebrow">DATA GOVERNANCE</span><p className="muted">Warehouse views expose aggregate operational facts only. No patient identifiers are included in these views or the county CSV export. Access follows the existing reports.read permission.</p></div>
  </section>;
}
