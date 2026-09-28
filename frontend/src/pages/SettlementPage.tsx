import { useState } from "react";
import { api } from "../api/client";

export default function SettlementPage(){
 const [claimId,setClaimId]=useState(""); const [payerId,setPayerId]=useState(""); const [batchId,setBatchId]=useState(""); const [obligationId,setObligationId]=useState(""); const [amount,setAmount]=useState(""); const [received,setReceived]=useState(""); const [method,setMethod]=useState("BANK_TRANSFER"); const [message,setMessage]=useState("");
 const run=async(fn:()=>Promise<any>)=>{try{const r=await fn();setMessage(JSON.stringify(r,null,2));}catch(e){setMessage(e instanceof Error?e.message:String(e));}};
 return <div className="page"><h1>Settlement & Provider Payments</h1><p>Turn adjudicated claims into payer obligations, settlement batches, provider payments and reconciliation records.</p>
 <section className="card"><h2>Settlement obligation</h2><input placeholder="Adjudicated claim UUID" value={claimId} onChange={e=>setClaimId(e.target.value)}/><button onClick={()=>run(()=>api.settlementCreateObligation({claim_id:claimId}))}>Generate obligation</button></section>
 <section className="card"><h2>Create batch</h2><input placeholder="Payer UUID" value={payerId} onChange={e=>setPayerId(e.target.value)}/><button onClick={()=>run(()=>api.settlementCreateBatch({payer_id:payerId}))}>Create settlement batch</button></section>
 <section className="card"><h2>Record provider payment</h2><input placeholder="Batch UUID" value={batchId} onChange={e=>setBatchId(e.target.value)}/><input placeholder="Obligation UUID" value={obligationId} onChange={e=>setObligationId(e.target.value)}/><input placeholder="Amount" value={amount} onChange={e=>setAmount(e.target.value)}/><input placeholder="Method" value={method} onChange={e=>setMethod(e.target.value)}/><button onClick={()=>run(()=>api.settlementRecordPayment(batchId,{obligation_id:obligationId,amount,method}))}>Record payment</button></section>
 <section className="card"><h2>Reconcile batch</h2><input placeholder="Batch UUID" value={batchId} onChange={e=>setBatchId(e.target.value)}/><input placeholder="Received amount" value={received} onChange={e=>setReceived(e.target.value)}/><button onClick={()=>run(()=>api.settlementReconcile(batchId,{received_amount:received}))}>Reconcile</button></section>
 <section className="card"><h2>Result</h2><pre>{message||"No operation run yet."}</pre></section></div>
}