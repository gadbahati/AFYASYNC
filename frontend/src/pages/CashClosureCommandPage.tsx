import {useEffect,useState} from "react";
import {api} from "../api/client";

export default function CashClosureCommandPage(){
  const [data,setData]=useState<any>(null); const [loading,setLoading]=useState(true); const [verifying,setVerifying]=useState(false); const [result,setResult]=useState<any>(null);
  async function load(){setLoading(true);try{setData(await api.cashClosureCommand(100));}finally{setLoading(false);}}
  async function verify(){setVerifying(true);try{const r=await api.cashClosureVerify(200);setResult(r);await load();}finally{setVerifying(false);}}
  useEffect(()=>{load();},[]);
  if(loading)return <section className="page"><h1>Cash Closure Command Centre</h1><p>Loading…</p></section>;
  return <section className="page">
    <div className="page-header"><div><h1>Cash Closure Command Centre</h1><p>Evidence-based view of revenue work, financial exposure, terminal closure and exceptions.</p></div><button className="primary" onClick={verify} disabled={verifying}>{verifying?"Verifying…":"Verify cash closure"}</button></div>
    <div className="card-grid">
      <div className="card"><span className="muted">Control status</span><strong>{data?.status??"—"}</strong></div>
      <div className="card"><span className="muted">Open work</span><strong>{data?.open_work??0}</strong></div>
      <div className="card"><span className="muted">Guardrail exposure</span><strong>{Number(data?.guardrail_exposure??0).toLocaleString()}</strong></div>
      <div className="card"><span className="muted">Recovery outstanding</span><strong>{Number(data?.recovery_outstanding??0).toLocaleString()}</strong></div>
      <div className="card"><span className="muted">Resolution exposure</span><strong>{Number(data?.resolution_exposure??0).toLocaleString()}</strong></div>
      <div className="card"><span className="muted">Exceptions</span><strong>{data?.exceptions??0}</strong></div>
    </div>
    <div className="card"><h2>Verified terminal outcomes</h2><p>Guardrails: <strong>{data?.terminal_guardrails??0}</strong> · Recoveries: <strong>{data?.terminal_recoveries??0}</strong> · Resolutions: <strong>{data?.terminal_resolutions??0}</strong></p></div>
    <div className="card"><h2>Exposure interpretation</h2><p>{data?.note}</p><p className="muted">This dashboard deliberately does not present overlapping operational signals as accounting loss or recovered cash.</p></div>
    {result&&<div className="card"><h2>Latest verification</h2><pre>{JSON.stringify(result,null,2)}</pre></div>}
  </section>
}
