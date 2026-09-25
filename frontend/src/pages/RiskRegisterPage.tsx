import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

export function RiskRegisterPage() {
  const [posture,setPosture]=useState<any>({}); const [risks,setRisks]=useState<any[]>([]);
  const [error,setError]=useState(""); const [loading,setLoading]=useState(false);
  const load=useCallback(async()=>{setLoading(true);setError("");try{const[p,r]=await Promise.all([api.riskPosture(),api.riskList()]);setPosture(p||{});setRisks(r?.risks||p?.risks||[])}catch(e){setError(e instanceof Error?e.message:"Unable to load risk register.")}finally{setLoading(false)}},[]);
  useEffect(()=>{void load()},[load]);
  const update=async(id:string,status:string)=>{try{await api.riskUpdate(id,{status});await load()}catch(e){setError(e instanceof Error?e.message:"Unable to update risk.")}};
  return <section className="page"><div className="page-header"><div><span className="eyebrow">PHASE 39</span><h1>Residual risk register</h1><p>Track operational, security, privacy, compliance and integration risks.</p></div><button className="secondary" onClick={()=>void load()} disabled={loading}>Refresh</button></div>
  {error&&<div className="notice error">{error}</div>}<div className="stats-grid"><div className="stat-card"><span>Posture</span><strong>{posture.band||"—"}</strong></div><div className="stat-card"><span>Total</span><strong>{posture.total??0}</strong></div><div className="stat-card"><span>Open</span><strong>{posture.open??0}</strong></div><div className="stat-card"><span>High/Critical open</span><strong>{posture.critical_or_high_open??0}</strong></div></div>
  <div className="card"><h2>Risk register</h2><div className="table-wrap"><table><thead><tr><th>Code</th><th>Risk</th><th>Category</th><th>Residual</th><th>Status</th><th>Owner</th><th>Action</th></tr></thead><tbody>{risks.map((x:any)=><tr key={x.id}><td>{x.code}</td><td>{x.title}<br/><small>{x.description}</small></td><td>{x.category}</td><td>{x.residual_level}</td><td>{x.status}</td><td>{x.owner||"—"}</td><td>{x.status==="OPEN"&&<button onClick={()=>void update(x.id,"MITIGATED")}>Mark mitigated</button>}{x.status!=="OPEN"&&<button className="secondary" onClick={()=>void update(x.id,"OPEN")}>Reopen</button>}</td></tr>)}</tbody></table></div></div>
  <div className="card"><p>{posture.note||"Residual risk is managed through accountable ownership and documented treatment."}</p></div></section>
}