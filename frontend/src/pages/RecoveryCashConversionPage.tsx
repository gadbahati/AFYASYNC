import {useEffect,useState} from "react";
import {api} from "../api/client";
type Row={case_id:string;case_number:string;expected:number;recovered:number;outstanding:number;conversion_rate:number;age_days:number;updates:number;status:string;priority:string;reason:string};
export default function RecoveryCashConversionPage(){
 const [rows,setRows]=useState<Row[]>([]),[totals,setTotals]=useState<any>({}),[aging,setAging]=useState<any>({}),[days,setDays]=useState(90);
 useEffect(()=>{api.get("/api/v1/contract-guardrails/recovery-cash-conversion?days="+days).then((r:any)=>{setRows(r.cases||[]);setTotals(r.totals||{});setAging(r.aging_outstanding||{})})},[days]);
 const m=(n:number)=>"KES "+Number(n||0).toLocaleString(undefined,{maximumFractionDigits:0});
 return <div className="page"><div className="page-header"><div><h1>Recovery & Cash Conversion</h1><p>Measure recovery cases from expected value to recovered cash, aging and operational follow-up.</p></div><select value={days} onChange={e=>setDays(Number(e.target.value))}><option value={30}>30 days</option><option value={90}>90 days</option><option value={180}>180 days</option><option value={365}>365 days</option></select></div>
 <div className="stat-grid"><div className="stat-card"><span>Expected recovery</span><strong>{m(totals.expected)}</strong></div><div className="stat-card"><span>Recovered</span><strong>{m(totals.recovered)}</strong></div><div className="stat-card"><span>Outstanding</span><strong>{m(totals.outstanding)}</strong></div><div className="stat-card"><span>Cash conversion</span><strong>{totals.conversion_rate||0}%</strong></div></div>
 <section className="card"><h2>Recovery aging</h2><p>0–7: {m(aging["0_7"])} · 8–30: {m(aging["8_30"])} · 31–60: {m(aging["31_60"])} · 61–90: {m(aging["61_90"])} · 91+: {m(aging["91_plus"])}</p></section>
 <section className="card"><h2>Recovery cases</h2><div className="table-wrap"><table><thead><tr><th>Case</th><th>Expected</th><th>Recovered</th><th>Outstanding</th><th>Conversion</th><th>Age</th><th>Activity</th><th>Status</th></tr></thead><tbody>{rows.map(x=><tr key={x.case_id}><td><strong>{x.case_number}</strong><br/><small>{x.reason}</small></td><td>{m(x.expected)}</td><td>{m(x.recovered)}</td><td>{m(x.outstanding)}</td><td>{x.conversion_rate}%</td><td>{x.age_days}d</td><td>{x.updates}</td><td>{x.status}</td></tr>)}</tbody></table></div></section>
 </div>
}
