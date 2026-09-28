import { useState } from "react";
import { api } from "../api/client";

export function AdjudicationPage() {
 const [claimId,setClaimId]=useState(""); const [result,setResult]=useState<any>(null); const [error,setError]=useState(""); const [loading,setLoading]=useState(false);
 async function run(){setLoading(true);setError("");try{setResult(await api.adjudicateClaim({claim_id:claimId.trim(),force:false}));}catch(e){setError(e instanceof Error?e.message:"ADJUDICATION_FAILED")}finally{setLoading(false)}}
 return <section className="page-stack">
  <div className="page-header"><div><p className="eyebrow">Phase 45 · Independent claims adjudication</p><h1>Claims adjudication engine</h1><p className="muted">Evaluate a claim against verified coverage, benefit rules and applicable preauthorization evidence before settlement.</p></div></div>
  {error&&<div className="error-banner">{error}</div>}
  <div className="card"><div className="card-header"><div><p className="eyebrow">Adjudication request</p><h2>Run independent decision</h2></div><span className="status-badge">PAYER-AGNOSTIC</span></div>
   <div className="form-grid"><label>Claim ID<input value={claimId} onChange={e=>setClaimId(e.target.value)} placeholder="UUID"/></label></div>
   <div className="form-actions"><button className="primary" disabled={loading||!claimId.trim()} onClick={()=>void run()}>{loading?"Adjudicating…":"Run adjudication"}</button></div>
  </div>
  {result&&<div className="card"><div className="card-header"><div><p className="eyebrow">Decision</p><h2>{result.decision}</h2></div><span className="status-badge">{result.reason_code}</span></div>
   <div className="stat-grid"><div className="stat-card"><span>Submitted</span><strong>{result.submitted_amount}</strong><small>Claimed amount</small></div><div className="stat-card"><span>Allowed</span><strong>{result.allowed_amount}</strong><small>Adjudicated payable</small></div><div className="stat-card"><span>Patient</span><strong>{result.patient_amount}</strong><small>Calculated patient amount</small></div><div className="stat-card"><span>Engine</span><strong>V1</strong><small>Independent rules evaluation</small></div></div>
   <div className="notice-box"><strong>Evidence</strong><span>{JSON.stringify(result.evidence||{})}</span></div>
  </div>}
 </section>;
}