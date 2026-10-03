import {useEffect,useState} from "react";
import {api} from "../api/client";
import {useWorkspace} from "../workspaces/WorkspaceContext";

export default function BusinessContinuityPage(){
  const {tenantId}=useWorkspace();
  const [data,setData]=useState<any>(null);
  const [error,setError]=useState("");
  async function load(){try{setData(await api.businessContinuityOverview());}catch(err:any){setError(err?.message||err?.code||"BCP_LOAD_FAILED");}}
  useEffect(()=>{void load();},[tenantId]);
  return <section className="page">
    <div className="page-header"><div><p className="muted">PHASE 120 · BUSINESS CONTINUITY</p><h1>Business Continuity Control Plane</h1><p className="muted">Tenant-level RTO, RPO, offline and recovery-test posture.</p></div></div>
    {error&&<div className="card"><p className="error">{error}</p></div>}
    {data&&<><div className="stat-grid" style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(170px,1fr))",gap:12}}><div className="stat-card"><div className="muted small">Organizations</div><div className="stat-value">{data.organizations}</div></div><div className="stat-card"><div className="muted small">Plans</div><div className="stat-value">{data.plans}</div></div><div className="stat-card"><div className="muted small">Tested ≤90d</div><div className="stat-value">{data.tested_within_90_days}</div></div><div className="stat-card"><div className="muted small">Stale / never tested</div><div className="stat-value">{data.stale_or_never_tested}</div></div></div><div className="card" style={{marginTop:18}}><h2>Continuity plans</h2><div className="table-wrap"><table><thead><tr><th>Tenant</th><th>Tier</th><th>RTO</th><th>RPO</th><th>Offline</th><th>Status</th></tr></thead><tbody>{(data.plans||[]).map((p:any)=><tr key={p.id}><td>{p.organization_id}</td><td>{p.service_tier}</td><td>{p.rto_minutes} min</td><td>{p.rpo_minutes} min</td><td>{p.offline_max_hours} h</td><td>{p.status}</td></tr>)}</tbody></table></div></div></>}
  </section>;
}
