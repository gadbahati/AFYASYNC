import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function RevenueAnomalyPage() {
  const [overview, setOverview] = useState<any>(null);
  const [cases, setCases] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [scanning, setScanning] = useState(false);

  async function load() {
    const [o, c] = await Promise.all([api.revenueAnomalyOverview(), api.revenueAnomalyCases()]);
    setOverview(o);
    setCases(c);
  }

  useEffect(() => { void load(); }, []);

  async function scan() {
    setScanning(true); setMessage("");
    try {
      const result = await api.revenueAnomalyScan(30);
      setMessage(`Scan complete: ${result.cases_opened} new investigation cases.`);
      await load();
    } catch (e) { setMessage(e instanceof Error ? e.message : String(e)); }
    finally { setScanning(false); }
  }

  async function updateCase(item: any) {
    const status = prompt("Status: OPEN, IN_REVIEW, CONFIRMED, DISMISSED, or RESOLVED", item.status);
    if (!status) return;
    const note = prompt("Investigation note (optional)", item.notes || "") ?? "";
    try { await api.revenueAnomalyUpdate(item.id, { status, note }); await load(); }
    catch (e) { setMessage(e instanceof Error ? e.message : String(e)); }
  }

  return <div className="page-stack">
    <div className="page-header"><div>
      <p className="eyebrow">Phase 59 · Revenue intelligence</p>
      <h1>Revenue Anomalies</h1>
      <p className="muted">Deterministic leakage and billing-integrity signals for human investigation.</p>
    </div><div>
      <button className="secondary" onClick={() => void load()}>Refresh</button>{" "}
      <button onClick={() => void scan()} disabled={scanning}>{scanning ? "Scanning…" : "Run 30-day scan"}</button>
    </div></div>
    {message && <div className="notice-box">{message}</div>}
    {overview && <div className="stat-grid">
      <div className="stat-card"><span>Open investigations</span><strong>{overview.open_cases}</strong></div>
      <div className="stat-card"><span>Amount at risk</span><strong>KES {Number(overview.amount_at_risk).toLocaleString()}</strong></div>
      {Object.entries(overview.by_severity || {}).map(([k,v]) => <div className="stat-card" key={k}><span>{k}</span><strong>{String(v)}</strong></div>)}
    </div>}
    <section className="card"><h2>Investigation queue</h2><div className="table-wrap"><table><thead><tr>
      <th>Case</th><th>Signal</th><th>Severity</th><th>Risk</th><th>Amount at risk</th><th>Status</th><th></th>
    </tr></thead><tbody>{cases.map(c => <tr key={c.id}>
      <td>{c.case_number}</td><td>{c.anomaly_type}</td><td>{c.severity}</td><td>{c.risk_score}</td>
      <td>KES {Number(c.amount_at_risk).toLocaleString()}</td><td>{c.status}</td>
      <td><button className="secondary" onClick={() => void updateCase(c)}>Review</button></td>
    </tr>)}</tbody></table></div></section>
  </div>;
}
