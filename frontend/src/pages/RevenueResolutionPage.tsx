import { useEffect,useState } from "react";
import { api } from "../api/client";
const money=(v:any)=>`KES ${Number(v||0).toLocaleString(undefined,{maximumFractionDigits:2})}`;
export default function RevenueResolutionPage(){
 const [overview,setOverview]=useState<any>(null),[cases,setCases]=useState<any[]>([]),[message,setMessage]=useState("");
 async function load(){const [o,c]=await Promise.all([api.revenueResolutionOverview(),api.revenueResolutionCases()]);setOverview(o);setCases(c);}
 async function sync(){try{const r=await api.revenueResolutionSync();setMessage(`Synchronized ${r.created} new resolution cases from ${r.candidates} revenue signals.`);await load();}catch(e){setMessage(e instanceof Error?e.message:String(e));}}
 async function update(id:string,status:string){try{await api.revenueResolutionUpdate(id,{status});await load();}catch(e){setMessage(e instanceof Error?e.message:String(e));}}
 useEffect(()=>{void load().catch(e=>setMessage(e instanceof Error?e.message:String(e)));},[]);
 return <div className="page-stack">
  <div className="page-header"><div><p className="eyebrow">Phase 63 · Revenue operations</p><h1>Revenue Resolution Centre</h1><p className="muted">One operational queue for denials, recovery, anomaly investigation and collections.</p></div><button className="secondary" onClick={()=>void sync()}>Sync revenue signals</button></div>
  {message&&<div className="notice-box">{message}</div>}
  {overview&&<div className="stat-grid">{Object.entries(overview.active_priorities||{}).map(([p,v]:[string,any])=><div className="stat-card" key={p}><span>{p}</span><strong>{v}</strong><small>active cases</small></div>)}</div>}
  <section className="card"><h2>Active resolution cases</h2><div className="table-wrap"><table><thead><tr><th>Priority</th><th>Source</th><th>Issue</th><th>At risk</th><th>Status</th><th>Due</th><th>Action</th></tr></thead><tbody>{cases.map(x=><tr key={x.id}><td>{x.priority}</td><td>{x.source_type}</td><td>{x.title}</td><td>{money(x.amount_at_risk)}</td><td>{x.status}</td><td>{x.due_at?new Date(x.due_at).toLocaleDateString():"—"}</td><td>{x.status!=="CLOSED"&&<><button className="secondary" onClick={()=>void update(x.id,"IN_REVIEW")}>Review</button>{" "}<button className="secondary" onClick={()=>void update(x.id,"RESOLVED")}>Resolve</button></>}</td></tr>)}</tbody></table></div></section>
 </div>;
}