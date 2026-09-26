import { useEffect, useState } from "react";
import { api } from "../api/client";

type Overview = any;

export function NationalFinancingExchangePage() {
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try { setData(await api.nationalFinancingOverview()); }
    catch (err) { setError(err instanceof Error ? err.message : "FINANCING_EXCHANGE_REQUEST_FAILED"); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  const capabilities = data?.capabilities ? Object.entries(data.capabilities) : [];
  return <section className="page-stack">
    <div className="page-header"><div><p className="eyebrow">Phase 41 · National challenger architecture</p><h1>National financing exchange</h1><p className="muted">A payer-agnostic financing control plane. SHA can participate, but the platform boundary is the patient, provider and financing network—not a single payer.</p></div><button type="button" className="secondary" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button></div>
    {error && <div className="error-banner">{error}</div>}
    {loading && !data ? <div className="card"><p className="muted">Loading financing exchange posture…</p></div> : data && <>
      <div className="stat-grid"><div className="stat-card"><span>Active payers</span><strong>{data.active_payers}</strong><small>National financing participants</small></div><div className="stat-card"><span>Active plans</span><strong>{data.active_plans}</strong><small>Benefit plans available to route</small></div><div className="stat-card"><span>Claims</span><strong>{data.claims.count}</strong><small>Across the financing network</small></div><div className="stat-card"><span>Pending claims</span><strong>{data.claims.pending_count}</strong><small>Require financing operations</small></div></div>
      <div className="card"><div className="card-header"><div><p className="eyebrow">Core engine</p><h2>Payer-agnostic capabilities</h2><p className="muted">The same financing primitives should work across SHA, private insurance, employer schemes and future payers.</p></div><span className="status-badge">ACTIVE ARCHITECTURE</span></div><div className="table-wrap"><table><thead><tr><th>Capability</th><th>Status</th></tr></thead><tbody>{capabilities.map(([key,value]) => <tr key={key}><td>{String(key).replaceAll("_", " ")}</td><td><span className="status-badge">{value ? "READY" : "MISSING"}</span></td></tr>)}</tbody></table></div></div>
      <div className="card"><div className="card-header"><div><p className="eyebrow">Financing network</p><h2>Registered active payers</h2></div></div>{data.payers.length === 0 ? <div className="empty-state"><strong>No active payers yet</strong><span>Use Payer network to register and govern financing participants.</span></div> : <div className="table-wrap"><table><thead><tr><th>Payer</th><th>Code</th><th>Type</th><th>Status</th><th>Integration</th></tr></thead><tbody>{data.payers.map((p:any) => <tr key={p.id}><td><strong>{p.name}</strong></td><td>{p.code}</td><td>{p.type}</td><td><span className="status-badge">{p.status}</span></td><td>{p.integration_status}</td></tr>)}</tbody></table></div>}</div>
      <div className="card"><p className="eyebrow">Strategic boundary</p><h2>SHA is an integration, not the operating-system boundary</h2><p className="muted">{data.position}</p><div className="notice-box"><strong>Next build targets</strong><span>Universal health identity → benefit/rule engine → multi-payer eligibility → authorisation → claim adjudication → settlement → fraud intelligence → patient financing.</span></div></div>
    </>}
  </section>;
}
