import {useEffect,useState} from "react";
import {api} from "../api/client";
export default function RevenueActionPrioritiesPage(){
 const [d,setD]=useState<any>({items:[]});
 useEffect(()=>{api.get("/api/v1/contract-guardrails/revenue-action-priorities?limit=100").then(setD)},[]);
 const m=(n:number)=>"KES "+Number(n||0).toLocaleString(undefined,{maximumFractionDigits:0});
 return <div className="page"><div className="page-header"><div><h1>Revenue Action Priorities</h1><p>Ranked financial-control work based on severity, age and exposure.</p></div></div>
 <section className="card"><h2>Priority queue ({d.count||0})</h2><div className="table-wrap"><table><thead><tr><th>Priority</th><th>Source</th><th>Issue</th><th>Severity</th><th>Exposure</th><th>Recommended action</th></tr></thead><tbody>{(d.items||[]).map((x:any)=><tr key={x.source+"-"+x.source_id}><td><strong>{x.priority_score}</strong></td><td>{x.source}</td><td>{x.title}</td><td>{x.severity}</td><td>{m(x.amount)}</td><td>{x.recommended_action}</td></tr>)}</tbody></table></div></section>
 <section className="card"><p>Priority scores are operational triage signals. They do not establish fraud, fault or final accounting loss.</p></section>
 </div>
}
