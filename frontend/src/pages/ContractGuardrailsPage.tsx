import {useEffect,useState} from "react";

const base=import.meta.env.VITE_API_URL||"";
const headers=()=>({Authorization:"Bearer "+(localStorage.getItem("access_token")||""),"Content-Type":"application/json"});
async function req(path:string,options:any={}){const r=await fetch(base+path,{...options,headers:{...headers(),...(options.headers||{})}});if(!r.ok)throw new Error(await r.text()||"Request failed");return r.json();}

export default function ContractGuardrailsPage(){
 const[data,setData]=useState<any>({total:0,open:0,at_risk:0,statuses:{}}); const[items,setItems]=useState<any[]>([]);
 const[error,setError]=useState(""); const[busy,setBusy]=useState("");
 const load=async()=>{try{const [o,g]=await Promise.all([req("/api/v1/contract-guardrails/overview"),req("/api/v1/contract-guardrails?limit=200")]);setData(o);setItems(g);setError("")}catch(e:any){setError(e.message)}};
 useEffect(()=>{load()},[]);
 const closeLoop=async()=>{setBusy("loop");try{await req("/api/v1/contract-guardrails/close-loop",{method:"POST",body:JSON.stringify({limit:200})});await load()}catch(e:any){setError(e.message)}finally{setBusy("")}};
 const sync=async()=>{setBusy("sync");try{await req("/api/v1/contract-guardrails/sync",{method:"POST",body:JSON.stringify({limit:200})});await load()}catch(e:any){setError(e.message)}finally{setBusy("")}};
 const update=async(id:string,status:string)=>{setBusy(id);try{await req("/api/v1/contract-guardrails/"+id,{method:"PATCH",body:JSON.stringify({status})});await load()}catch(e:any){setError(e.message)}finally{setBusy("")}};
 const money=(n:number)=>"KES "+Number(n||0).toLocaleString(undefined,{maximumFractionDigits:0});
 return <div className="page">
  <div className="page-header"><div><h1>Contract Compliance Guardrails</h1><p>Monitor the contract → tariff → claim → adjudication → payment chain and surface revenue-impacting deviations.</p></div><div><button disabled={busy==="sync"} onClick={sync}>{busy==="sync"?"Scanning…":"Run guardrail scan"}</button> <button disabled={busy==="loop"} onClick={closeLoop}>{busy==="loop"?"Processing…":"Push to recovery & work queue"}</button></div></div>
  {error&&<div className="alert">{error}</div>}
  <div className="grid grid-3">
   <div className="card"><strong>{data.total}</strong><span>Total guardrails</span></div>
   <div className="card"><strong>{data.open}</strong><span>Open / active</span></div>
   <div className="card"><strong>{money(data.at_risk)}</strong><span>Amount at risk</span></div>
  </div>
  <div className="card"><h2>Operational guardrail queue</h2>
   <div className="table-wrap"><table><thead><tr><th>Severity</th><th>Guardrail</th><th>Claim</th><th>Expected</th><th>Actual</th><th>Risk</th><th>Status</th><th>Action</th></tr></thead>
   <tbody>{items.map(x=><tr key={x.id}><td><strong>{x.severity}</strong></td><td><strong>{x.guardrail_type}</strong><br/><span className="muted small">{x.title}</span></td><td className="small">{x.claim_id||"—"}</td><td>{money(x.expected_amount)}</td><td>{money(x.actual_amount)}</td><td><strong>{money(x.amount_at_risk)}</strong></td><td>{x.status}</td><td>{x.status==="RESOLVED"||x.status==="DISMISSED"?<span>Closed</span>:<select value={x.status} disabled={busy===x.id} onChange={e=>update(x.id,e.target.value)}><option>OPEN</option><option>IN_REVIEW</option><option>RESOLVED</option><option>DISMISSED</option></select>}</td></tr>)}</tbody></table></div>
   {!items.length&&<p>No contract compliance guardrails are currently recorded. Run a scan after claims and contract terms exist.</p>}
  </div>
  <div className="card"><h2>What this protects</h2><p><strong>Tariff configuration gaps</strong> identify services without an active contracted tariff. <strong>Tariff breaches</strong> compare submitted claim value with activated contract terms. <strong>Adjudication variance</strong> identifies allowed amounts below the activated tariff envelope. <strong>Payment variance</strong> surfaces terminal claims where paid value is below the approved amount.</p></div>
 </div>;
}
