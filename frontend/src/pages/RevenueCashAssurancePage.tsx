import {useEffect,useState} from "react";
import {api} from "../api/client";

export default function RevenueCashAssurancePage(){
 const [d,setD]=useState<any>(null); const [loading,setLoading]=useState(true);
 async function load(){setLoading(true);try{setD(await api.cashClosureAssurance());}finally{setLoading(false);}}
 useEffect(()=>{load();},[]);
 if(loading)return <section className="page"><h1>Revenue & Cash Assurance</h1><p>Loading…</p></section>;
 return <section className="page">
  <div className="page-header"><div><h1>Revenue & Cash Assurance</h1><p>Facility-level assurance across guardrails, recovery, resolution and operational work.</p></div><button className="secondary" onClick={load}>Refresh assurance</button></div>
  <div className="card-grid">
   <div className="card"><span className="muted">Assurance state</span><strong>{d?.assurance??"—"}</strong></div>
   <div className="card"><span className="muted">Operational state</span><strong>{d?.status??"—"}</strong></div>
   <div className="card"><span className="muted">Operational exposure</span><strong>{Number(d?.operational_exposure??0).toLocaleString()}</strong></div>
   <div className="card"><span className="muted">Exceptions</span><strong>{d?.exceptions??0}</strong></div>
  </div>
  <div className="card"><h2>Assurance controls</h2>{(d?.actions??[]).map((x:any)=><div key={x.action} className="list-row"><span>{x.action}</span><strong>{x.count}</strong></div>)}</div>
  <div className="card"><h2>Exposure by control layer</h2>{(d?.categories??[]).map((x:any)=><div key={x.key} className="list-row"><span>{x.key} · {x.open} open</span><strong>{Number(x.exposure??0).toLocaleString()}</strong></div>)}</div>
  <div className="card"><h2>Control interpretation</h2><p>{d?.note}</p></div>
 </section>
}
