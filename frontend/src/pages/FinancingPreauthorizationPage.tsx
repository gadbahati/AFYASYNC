import { useState } from "react";
import { api } from "../api/client";

export function FinancingPreauthorizationPage() {
  const [personId,setPersonId]=useState(""); const [coverageId,setCoverageId]=useState(""); const [payerId,setPayerId]=useState("");
  const [serviceCode,setServiceCode]=useState(""); const [serviceType,setServiceType]=useState(""); const [amount,setAmount]=useState("0");
  const [result,setResult]=useState<any>(null); const [error,setError]=useState(""); const [loading,setLoading]=useState(false);

  async function request() { setLoading(true);setError("");setResult(null);try{setResult(await api.financingPreauthCreate({person_id:personId.trim(),coverage_id:coverageId.trim(),payer_id:payerId.trim(),service_code:serviceCode.trim()||null,service_type:serviceType.trim()||null,requested_amount:Number(amount||0)}));}catch(e){setError(e instanceof Error?e.message:"PREAUTH_REQUEST_FAILED")}finally{setLoading(false)}}
  async function decide(status:string){if(!result)return;setLoading(true);setError("");try{setResult(await api.financingPreauthDecide(result.id,{status,approved_amount:Number(status==="REJECTED"?0:amount),external_reference:null}));}catch(e){setError(e instanceof Error?e.message:"PREAUTH_DECISION_FAILED")}finally{setLoading(false)}}

  return <section className="page-stack">
    <div className="page-header"><div><p className="eyebrow">Phase 44 · Multi-payer financing</p><h1>Preauthorization exchange</h1><p className="muted">A single preauthorization contract driven by the universal eligibility engine, independent of which financing participant is behind the coverage.</p></div></div>
    {error&&<div className="error-banner">{error}</div>}
    <div className="card"><div className="card-header"><div><p className="eyebrow">Request</p><h2>Ask for financing authorization</h2></div><span className="status-badge">PAYER AGNOSTIC</span></div>
      <div className="form-grid">
        <label>Person ID<input value={personId} onChange={e=>setPersonId(e.target.value)} placeholder="UUID"/></label>
        <label>Coverage ID<input value={coverageId} onChange={e=>setCoverageId(e.target.value)} placeholder="UUID"/></label>
        <label>Payer ID<input value={payerId} onChange={e=>setPayerId(e.target.value)} placeholder="UUID"/></label>
        <label>Service code<input value={serviceCode} onChange={e=>setServiceCode(e.target.value)} placeholder="e.g. MRI-BRAIN"/></label>
        <label>Service type<input value={serviceType} onChange={e=>setServiceType(e.target.value)} placeholder="e.g. IMAGING"/></label>
        <label>Requested amount<input type="number" min="0" step="0.01" value={amount} onChange={e=>setAmount(e.target.value)}/></label>
      </div>
      <div className="form-actions"><button className="primary" disabled={loading||!personId||!coverageId||!payerId} onClick={()=>void request()}>{loading?"Checking…":"Request preauthorization"}</button></div>
    </div>
    {result&&<div className="card"><div className="card-header"><div><p className="eyebrow">Authorization</p><h2>{result.status}</h2></div><span className="status-badge">{result.authorization_number}</span></div>
      <div className="stat-grid"><div className="stat-card"><span>Requested</span><strong>{result.requested_amount}</strong><small>Financing request</small></div><div className="stat-card"><span>Approved</span><strong>{result.approved_amount}</strong><small>Authorized amount</small></div><div className="stat-card"><span>Payer</span><strong>{result.payer_id?"RESOLVED":"—"}</strong><small>Underlying financing participant</small></div><div className="stat-card"><span>Reason</span><strong>{result.decision_reason||"—"}</strong><small>Decision state</small></div></div>
      {result.status==="PENDING"&&<div className="form-actions"><button className="primary" disabled={loading} onClick={()=>void decide("AUTHORIZED")}>Authorize</button><button className="secondary" disabled={loading} onClick={()=>void decide("CONDITIONAL")}>Conditional</button><button className="secondary" disabled={loading} onClick={()=>void decide("REJECTED")}>Reject</button></div>}
    </div>}
  </section>
}