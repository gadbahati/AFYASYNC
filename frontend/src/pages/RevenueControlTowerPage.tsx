import {useEffect,useState} from "react";
import {api} from "../api/client";
export default function RevenueControlTowerPage(){
 const [d,setD]=useState<any>({signals:{},alerts:[]}),[days,setDays]=useState(30);
 useEffect(()=>{api.get("/api/v1/contract-guardrails/revenue-control-tower?days="+days).then(setD)},[days]);
 return <div className="page"><div className="page-header"><div><h1>Revenue Control Tower</h1><p>Operational signals requiring financial control-team attention.</p></div><select value={days} onChange={e=>setDays(Number(e.target.value))}><option value={7}>7 days</option><option value={30}>30 days</option><option value={90}>90 days</option><option value={365}>365 days</option></select></div>
 <div className="stat-grid"><div className="stat-card"><span>Control status</span><strong>{d.control_status||"—"}</strong></div><div className="stat-card"><span>Claim rejections</span><strong>{d.signals.claim_rejections||0}</strong></div><div className="stat-card"><span>Guardrails</span><strong>{d.signals.guardrails||0}</strong></div><div className="stat-card"><span>Recovery cases</span><strong>{d.signals.recovery||0}</strong></div></div>
 <section className="card"><h2>Active control signals</h2>{(d.alerts||[]).map((x:any,i:number)=><div className="list-row" key={i}><strong>{x.signal}</strong><span>{x.severity} · {x.count}</span></div>)}{!(d.alerts||[]).length&&<p>No active control signals detected for this window.</p>}</section>
 <section className="card"><h2>Operating model</h2><p>This tower is a control signal layer, not an automated fraud finding. Teams should inspect the underlying claim, contract, recovery and resolution records before taking action.</p></section>
 </div>
}
