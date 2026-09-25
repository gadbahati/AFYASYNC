import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

export function NationalReadinessPage() {
  const [data,setData]=useState<any>({}); const [error,setError]=useState(""); const [loading,setLoading]=useState(false);
  const load=useCallback(async()=>{setLoading(true);setError("");try{setData(await api.nationalReadiness())}catch(e){setError(e instanceof Error?e.message:"Unable to load national readiness.")}finally{setLoading(false)}},[]);
  useEffect(()=>{void load()},[load]);
  return <section className="page"><div className="page-header"><div><span className="eyebrow">PHASE 40 — FINAL PHASE</span><h1>National readiness declaration</h1><p>Aggregated software gates for pilot-scale operational readiness.</p></div><button className="secondary" onClick={()=>void load()} disabled={loading}>Refresh</button></div>
  {error&&<div className="notice error">{error}</div>}
  <div className="card"><h2>{data.title||"Final national readiness declaration"}</h2><div className="stats-grid"><div className="stat-card"><span>Overall</span><strong>{data.overall||"—"}</strong></div><div className="stat-card"><span>Band</span><strong>{data.overall_band||"—"}</strong></div><div className="stat-card"><span>Red gates</span><strong>{(data.reds||[]).length}</strong></div><div className="stat-card"><span>Amber gates</span><strong>{(data.ambers||[]).length}</strong></div></div></div>
  <div className="card"><h2>Readiness gates</h2><div className="table-wrap"><table><thead><tr><th>Gate</th><th>Band</th><th>Result</th></tr></thead><tbody>{Object.entries(data.gate_bands||{}).map(([k,v]:any)=><tr key={k}><td>{k.replaceAll("_"," ")}</td><td>{v}</td><td>{data.gates?.[k]?.ok===false?"CHECK FAILED":"CHECKED"}</td></tr>)}</tbody></table></div></div>
  <div className="grid-2"><div className="card"><h2>Capability summary</h2><ul>{(data.capability_summary||[]).map((x:string)=><li key={x}>{x}</li>)}</ul></div><div className="card"><h2>Operator-owned remaining</h2><ul>{(data.operator_owned_remaining||[]).map((x:string)=><li key={x}>{x}</li>)}</ul></div></div>
  <div className="card"><h2>Readiness statement</h2><p>{data.statement||"No declaration loaded."}</p><p><strong>Developer:</strong> {data.developer||"—"}</p><small>Generated: {data.generated_at||"—"}</small></div></section>;
}