import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

export function PerformancePage() {
  const [acceptance, setAcceptance] = useState<any>({});
  const [catalogue, setCatalogue] = useState<any>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [a, c] = await Promise.all([api.performanceAcceptance(), api.performanceCatalogue()]);
      setAcceptance(a || {}); setCatalogue(c || {});
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to load performance acceptance."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return <section className="page">
    <div className="page-header"><div><span className="eyebrow">PHASE 38</span><h1>Performance acceptance</h1><p>Runtime acceptance targets and load-test scenarios.</p></div><button className="secondary" onClick={() => void load()} disabled={loading}>Refresh</button></div>
    {error && <div className="notice error">{error}</div>}
    <div className="stats-grid">
      <div className="stat-card"><span>Verdict</span><strong>{acceptance.verdict || "—"}</strong></div>
      <div className="stat-card"><span>Band</span><strong>{acceptance.band || "—"}</strong></div>
      <div className="stat-card"><span>Requests</span><strong>{acceptance.sample_requests ?? 0}</strong></div>
      <div className="stat-card"><span>Timed requests</span><strong>{acceptance.timed_requests ?? 0}</strong></div>
    </div>
    <div className="card"><h2>Acceptance results</h2><div className="table-wrap"><table><thead><tr><th>Target</th><th>Observed</th><th>Threshold</th><th>Status</th><th>Warmup</th></tr></thead><tbody>
      {(acceptance.results || []).map((x:any) => <tr key={x.id}><td>{x.name}</td><td>{x.observed}</td><td>{x.target_max !== undefined ? "≤ " + x.target_max : "≥ " + x.target_min}</td><td>{x.ok ? "PASS" : "FAIL"}</td><td>{x.warmup ? "YES" : "NO"}</td></tr>)}
    </tbody></table></div></div>
    <div className="card"><h2>Load scenarios</h2><div className="table-wrap"><table><thead><tr><th>Scenario</th><th>Concurrent users</th><th>Duration</th><th>Focus</th></tr></thead><tbody>
      {(catalogue.scenarios || []).map((x:any) => <tr key={x.id}><td>{x.name}</td><td>{x.concurrent_users}</td><td>{x.duration_minutes} min</td><td>{(x.focus || []).join(", ")}</td></tr>)}
    </tbody></table></div><p>National-scale proof requires an external load generator such as k6 or Locust; this API evaluates process-local runtime metrics.</p></div>
  </section>;
}