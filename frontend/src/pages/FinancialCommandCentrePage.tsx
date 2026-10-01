import { useEffect, useState } from "react";
import { api } from "../api/client";

const money = (v:any) => `KES ${Number(v || 0).toLocaleString(undefined,{maximumFractionDigits:2})}`;

export default function FinancialCommandCentrePage() {
  const [overview,setOverview]=useState<any>(null);
  const [forecast,setForecast]=useState<any>(null);
  const [payers,setPayers]=useState<any[]>([]);
  const [days,setDays]=useState(90);
  const [message,setMessage]=useState("");

  async function load() {
    const [o,f,p]=await Promise.all([
      api.financialOverview(days),
      api.financialForecast(days),
      api.financialPayers(days)
    ]);
    setOverview(o); setForecast(f); setPayers(p);
  }

  useEffect(()=>{ void load().catch(e=>setMessage(e instanceof Error?e.message:String(e))); },[days]);

  return <div className="page-stack">
    <div className="page-header"><div>
      <p className="eyebrow">Phase 60 · Financial intelligence</p>
      <h1>Financial Command Centre</h1>
      <p className="muted">Live facility revenue, collections, receivables, recovery exposure and transparent cash-flow projections.</p>
    </div><div>
      <select value={days} onChange={e=>setDays(Number(e.target.value))}>
        <option value={30}>30 days</option><option value={90}>90 days</option><option value={180}>180 days</option><option value={365}>365 days</option>
      </select>{" "}<button className="secondary" onClick={()=>void load()}>Refresh</button>
    </div></div>
    {message&&<div className="notice-box">{message}</div>}
    {overview&&<div className="stat-grid">
      <div className="stat-card"><span>Billed</span><strong>{money(overview.billed)}</strong></div>
      <div className="stat-card"><span>Collected</span><strong>{money(overview.collected)}</strong><small>{overview.collection_rate}% collection rate</small></div>
      <div className="stat-card"><span>Claims receivable</span><strong>{money(overview.claims_receivable)}</strong></div>
      <div className="stat-card"><span>Recovery outstanding</span><strong>{money(overview.recovery_outstanding)}</strong></div>
      <div className="stat-card"><span>Anomaly exposure</span><strong>{money(overview.anomaly_amount_at_risk)}</strong></div>
    </div>}
    {forecast&&<section className="card"><h2>Cash-flow baseline forecast</h2>
      <p className="muted">Based on the recent daily run-rate from recorded billing and confirmed/recorded collections. It is a planning baseline, not a guarantee.</p>
      <div className="table-wrap"><table><thead><tr><th>Horizon</th><th>Projected billing</th><th>Projected collections</th><th>Projected net cash</th></tr></thead>
      <tbody>{[30,60,90].map(h=><tr key={h}><td>{h} days</td><td>{money(forecast.forecast?.[String(h)]?.projected_billing)}</td><td>{money(forecast.forecast?.[String(h)]?.projected_cash_collection)}</td><td>{money(forecast.forecast?.[String(h)]?.projected_net_cash)}</td></tr>)}</tbody></table></div>
      <p className="muted">Daily billing run-rate: {money(forecast.daily_billing_run_rate)} · Daily cash run-rate: {money(forecast.daily_cash_run_rate)} · Cash volatility: {forecast.cash_volatility_percent}%</p>
    </section>}
    <section className="card"><h2>Payer performance</h2><div className="table-wrap"><table><thead><tr><th>Payer</th><th>Claims</th><th>Submitted</th><th>Approved</th><th>Paid</th><th>Approval</th><th>Collection</th><th>Outstanding</th></tr></thead>
    <tbody>{payers.map(p=><tr key={p.payer_id}><td>{p.payer_id}</td><td>{p.claims}</td><td>{money(p.submitted)}</td><td>{money(p.approved)}</td><td>{money(p.paid)}</td><td>{p.approval_rate}%</td><td>{p.collection_rate}%</td><td>{money(p.outstanding)}</td></tr>)}</tbody></table></div></section>
  </div>;
}
