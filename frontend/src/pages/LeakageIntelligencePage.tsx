import {useEffect,useState} from "react";
import {api} from "../api/client";
type Row={payer_id:string;payer_name:string;denial_value:number;guardrail_exposure:number;recovery_outstanding:number;resolution_exposure:number;attributable_exposure:number;operational_exposure:number;recovery_yield_proxy:number};
export default function LeakageIntelligencePage(){
 const [rows,setRows]=useState<Row[]>([]),[totals,setTotals]=useState<any>({}),[days,setDays]=useState(90);
 useEffect(()=>{api.get("/api/v1/contract-guardrails/leakage-intelligence?days="+days).then((r:any)=>{setRows(r.payers||[]);setTotals(r.totals||{})})},[days]);
 const m=(n:number)=>"KES "+Number(n||0).toLocaleString(undefined,{maximumFractionDigits:0});
 return <div className="page"><div className="page-header"><div><h1>Revenue Leakage Intelligence</h1><p>Attribute financial exposure to denials, contract variance, recovery and unresolved revenue workflows.</p></div><select value={days} onChange={e=>setDays(Number(e.target.value))}><option value={30}>30 days</option><option value={90}>90 days</option><option value={180}>180 days</option><option value={365}>365 days</option></select></div>
 <div className="stat-grid"><div className="stat-card"><span>Attributable exposure</span><strong>{m(totals.attributable_exposure)}</strong></div><div className="stat-card"><span>Payment gap</span><strong>{m(totals.payment_gap)}</strong></div><div className="stat-card"><span>Recovery outstanding</span><strong>{m(totals.recovery_outstanding)}</strong></div><div className="stat-card"><span>Recovery yield proxy</span><strong>{totals.recovery_yield_proxy||0}%</strong></div></div>
 <section className="card"><h2>Leakage by payer</h2><div className="table-wrap"><table><thead><tr><th>Payer</th><th>Denial value</th><th>Contract variance</th><th>Recovery open</th><th>Resolution</th><th>Attributable</th><th>Yield proxy</th></tr></thead><tbody>{rows.map(x=><tr key={x.payer_id}><td><strong>{x.payer_name}</strong></td><td>{m(x.denial_value)}</td><td>{m(x.guardrail_exposure)}</td><td>{m(x.recovery_outstanding)}</td><td>{m(x.resolution_exposure)}</td><td><strong>{m(x.attributable_exposure)}</strong></td><td>{x.recovery_yield_proxy}%</td></tr>)}</tbody></table></div></section>
 <section className="card"><h2>Interpretation</h2><p>The recovery-yield figure is a management proxy, not an accounting recognition of recovered cash. Exposure categories can overlap, so investigate the linked underlying cases before treating totals as additive cash loss.</p></section>
 </div>
}
