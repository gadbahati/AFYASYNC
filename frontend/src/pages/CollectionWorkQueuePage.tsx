import { useEffect,useState } from "react";
import { api } from "../api/client";

const money=(v:any)=>`KES ${Number(v||0).toLocaleString(undefined,{maximumFractionDigits:2})}`;

export default function CollectionWorkQueuePage(){
  const [items,setItems]=useState<any[]>([]); const [overview,setOverview]=useState<any>(null); const [message,setMessage]=useState("");
  async function load(){ const [o,i]=await Promise.all([api.collectionWorkOverview(),api.collectionWork()]); setOverview(o); setItems(i); }
  async function sync(){ setMessage(""); try{ await api.syncCollectionWork(); await load(); setMessage("Collection priorities synchronized."); }catch(e){setMessage(e instanceof Error?e.message:String(e));}}
  async function update(id:string,status:string){ try{await api.updateCollectionWork(id,{status}); await load();}catch(e){setMessage(e instanceof Error?e.message:String(e));}}
  useEffect(()=>{void load().catch(e=>setMessage(e instanceof Error?e.message:String(e)));},[]);
  return <div className="page-stack">
    <div className="page-header"><div><p className="eyebrow">Phase 62 · Financial operations</p><h1>Collection Work Queue</h1><p className="muted">Turn receivables into owned, trackable work with status, deadlines and audit history.</p></div><button className="secondary" onClick={()=>void sync()}>Sync priorities</button></div>
    {message&&<div className="notice-box">{message}</div>}
    {overview&&<div className="stat-grid">{Object.entries(overview.statuses||{}).map(([s,v]: [string, any])=><div className="stat-card" key={s}><span>{s}</span><strong>{v.count}</strong><small>{money(v.outstanding_amount)}</small></div>)}</div>}
    <section className="card"><h2>Work items</h2><div className="table-wrap"><table><thead><tr><th>Priority</th><th>Type</th><th>Outstanding</th><th>Status</th><th>Due</th><th>Action</th></tr></thead><tbody>{items.map(x=><tr key={x.id}><td>{x.priority}</td><td>{x.title}</td><td>{money(x.outstanding_amount)}</td><td>{x.status}</td><td>{x.due_at?new Date(x.due_at).toLocaleDateString():"—"}</td><td>{x.status!=="DONE"&&<><button className="secondary" onClick={()=>void update(x.id,"IN_PROGRESS")}>Start</button>{" "}<button className="secondary" onClick={()=>void update(x.id,"DONE")}>Complete</button></>}</td></tr>)}</tbody></table></div></section>
  </div>;
}