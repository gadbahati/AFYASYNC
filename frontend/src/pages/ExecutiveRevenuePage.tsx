import {useEffect,useState} from "react";
import {api} from "../api/client";
export default function ExecutiveRevenuePage(){
 const [d,setD]=useState<any>({}),[days,setDays]=useState(90);
 useEffect(()=>{api.get("/api/v1/contract-guardrails/executive-revenue?days="+days).then(setD)},[days]);
 const m=(n:number)=>"KES "+Number(n||0).toLocaleString(undefined,{maximumFractionDigits:0});
 return <div className="page"><div className="page-header"><div><h1>Executive Revenue Command Centre</h1><p>Facility-level financial control across claims, payment gaps, contract compliance, recovery, resolution and operational work.</p></div><select value={days} onChange={e=>setDays(Number(e.target.value))}><option value={30}>30 days</option><option value={90}>90 days</option><option value={180}>180 days</option><option value={365}>365 days</option></select></div>
 <div className="stat-grid"><div className="stat-card"><span>Billed</span><strong>{m(d.claims?.billed)}</strong></div><div className="stat-card"><span>Paid</span><strong>{m(d.claims?.paid)}</strong></div><div className="stat-card"><span>Payment gap</span><strong>{m(d.claims?.payment_gap)}</strong></div><div className="stat-card"><span>Combined exposure</span><strong>{m(d.combined_exposure)}</strong></div></div>
 <div className="stat-grid"><div className="stat-card"><span>Guardrail risk</span><strong>{m(d.guardrails?.amount_at_risk)}</strong></div><div className="stat-card"><span>Recovery outstanding</span><strong>{m(d.recovery?.outstanding)}</strong></div><div className="stat-card"><span>Resolution risk</span><strong>{m(d.resolution?.amount_at_risk)}</strong></div><div className="stat-card"><span>Collection work</span><strong>{d.collection_work?.open||0}</strong></div></div>
 <section className="card"><h2>Executive action queue</h2>{(d.actions||[]).map((x:any,i:number)=><div className="list-row" key={i}><strong>{x.action}</strong><span>{x.priority} · {m(x.amount)}</span></div>)}</section>
 <section className="card"><h2>Control metrics</h2><p>{d.claims?.count||0} claims · {d.claims?.collection_rate||0}% collection rate · {d.guardrails?.open||0} open guardrails · {d.collection_work?.open||0} open financial work items.</p><p>Combined exposure is an operational signal and may overlap across linked workflows; it should not be treated as additive accounting loss.</p></section>
 </div>
}
