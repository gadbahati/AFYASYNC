import {useEffect,useState} from "react";

const base=import.meta.env.VITE_API_URL||"";
const headers=()=>({Authorization:"Bearer "+(localStorage.getItem("access_token")||""),"Content-Type":"application/json"});
async function req(path:string,options:any={}){const r=await fetch(base+path,{...options,headers:{...headers(),...(options.headers||{})}});if(!r.ok)throw new Error(await r.text()||"Request failed");return r.json();}

export default function ContractActivationPage(){
 const[data,setData]=useState<any>({total:0,not_activated:0,activated:0,partial:0,no_terms:0,contracts:[]});
 const[error,setError]=useState(""); const[busy,setBusy]=useState("");
 const load=async()=>{try{setData(await req("/api/v1/contract-activation/overview"));setError("")}catch(e:any){setError(e.message)}};
 useEffect(()=>{load()},[]);
 const activate=async(id:string)=>{
   setBusy(id);setError("");
   try{const result=await req("/api/v1/contract-activation/"+id+"/activate",{method:"POST",body:JSON.stringify({})}); 
     if(result.activation_status==="NO_APPLICABLE_TERMS") setError("Contract executed, but no recognized operational terms were available to activate.");
     await load();
   }catch(e:any){setError(e.message)}finally{setBusy("")}
 };
 return <div className="page">
   <div className="page-header"><div><h1>Contract Activation</h1><p>Propagate executed payer terms into tariffs, SLA controls, claims workflow and network participation.</p></div></div>
   {error&&<div className="alert">{error}</div>}
   <div className="grid grid-3">
     <div className="card"><strong>{data.not_activated}</strong><span>Awaiting activation</span></div>
     <div className="card"><strong>{data.activated}</strong><span>Activated</span></div>
     <div className="card"><strong>{data.partial}</strong><span>Partial activation</span></div>
   </div>
   <div className="card">
    <h2>Executed Contract Queue</h2>
    <p>Only contracts already executed by the approval workflow can be activated.</p>
    <div className="table-wrap"><table><thead><tr><th>Contract</th><th>Network</th><th>Execution</th><th>Activation</th><th>Action</th></tr></thead>
    <tbody>{(data.contracts||[]).map((c:any)=><tr key={c.id}><td><strong>{c.reference}</strong></td><td>{c.network_code}</td><td>{c.execution_status}</td><td>{c.activation_status}</td><td>{c.activation_status==="ACTIVATED"?<span>Active</span>:<button disabled={busy===c.id} onClick={()=>activate(c.id)}>{busy===c.id?"Activating…":"Activate terms"}</button>}</td></tr>)}</tbody></table></div>
    {!(data.contracts||[]).length&&<p>No executed contracts are currently waiting in the activation queue.</p>}
   </div>
   <div className="card"><h2>Activation controls</h2><p>Recognized terms include service tariffs, payment terms, payer SLA clocks, claims enablement and empanelment/network participation. Every activation stores a reconciliation summary and audit event.</p></div>
 </div>
}
