import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";

const money=(v:any)=>"KES "+Number(v||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const err=(e:unknown)=>e instanceof ApiError?(e.message||e.code):"Request failed";

type Patient={id:string;afya_id?:string;first_name:string;last_name:string;phone?:string};
type Wallet={person_id:string;wallet_id:string;currency:string;status:string;available_balance:number;total_contributions:number;total_applied:number;pending_patient_responsibility:number;transaction_count:number;transactions:any[]};

export function FinancingWalletPage(){
 const [patients,setPatients]=useState<Patient[]>([]);
 const [personId,setPersonId]=useState("");
 const [wallet,setWallet]=useState<Wallet|null>(null);
 const [loading,setLoading]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState("");
 const [amount,setAmount]=useState(""),[reference,setReference]=useState(""),[source,setSource]=useState("MANUAL");
 const [invoiceId,setInvoiceId]=useState(""),[applyAmount,setApplyAmount]=useState(""),[applyRef,setApplyRef]=useState("");

 const loadPatients=async()=>{try{const r=await api.listPatients(100,0);setPatients(r?.items||[])}catch(e){setError(err(e))}};
 const load=async(id=personId)=>{if(!id)return;setLoading(true);setError("");try{setWallet(await api.financingWallet(id,100));setPersonId(id)}catch(e){setError(err(e));setWallet(null)}finally{setLoading(false)}};
 useEffect(()=>{void loadPatients()},[]);

 const contribute=async()=>{if(!personId||!amount)return;setError("");setNotice("");try{await api.financingWalletContribution(personId,{amount:Number(amount),reference:reference||undefined,source_type:source,description:"Patient financing wallet contribution"});setAmount("");setReference("");setNotice("Contribution recorded in the wallet ledger.");await load()}catch(e){setError(err(e))}};
 const apply=async()=>{if(!personId||!invoiceId||!applyAmount)return;setError("");setNotice("");try{await api.financingWalletApply(personId,{invoice_id:invoiceId,amount:Number(applyAmount),reference:applyRef||undefined});setApplyAmount("");setApplyRef("");setNotice("Wallet funds applied to the patient invoice.");await load()}catch(e){setError(err(e))}};
 const reconcile=async()=>{if(!personId)return;setError("");setNotice("");try{await api.financingWalletReconcile(personId);setNotice("Wallet responsibility reconciliation completed.");await load()}catch(e){setError(err(e))}};

 return <div>
  <header className="page-header"><div><h1>Patient financing wallet</h1><p className="muted">A payer-agnostic financial wallet linking patient contributions, responsibility, invoices and financing activity.</p></div><button className="button secondary" onClick={()=>void load()}>Refresh</button></header>
  {error&&<div className="error" role="alert">{error}</div>}{notice&&<div className="info-box">{notice}</div>}
  <section className="card"><h2>Patient</h2><div style={{display:"flex",gap:10,alignItems:"end",flexWrap:"wrap"}}>
   <label style={{minWidth:320,flex:1}}>Select patient<select value={personId} onChange={e=>{setPersonId(e.target.value);void load(e.target.value)}}><option value="">Choose patient</option>{patients.map(p=><option key={p.id} value={p.id}>{p.first_name} {p.last_name} — {p.afya_id||p.id}</option>)}</select></label>
   {wallet&&<button className="button secondary" onClick={()=>void reconcile()}>Reconcile responsibility</button>}
  </div></section>
  {loading?<p className="muted">Loading financing wallet…</p>:wallet&&<>
   <div className="grid-3" style={{marginTop:16}}>
    <section className="card"><h3>Available balance</h3><strong>{money(wallet.available_balance)}</strong><p className="muted small">Derived from immutable wallet ledger credits minus debits.</p></section>
    <section className="card"><h3>Pending responsibility</h3><strong>{money(wallet.pending_patient_responsibility)}</strong><p className="muted small">Current patient-side financing exposure.</p></section>
    <section className="card"><h3>Total contributions</h3><strong>{money(wallet.total_contributions)}</strong><p className="muted small">Credits recorded to this wallet.</p></section>
   </div>
   <div className="grid-2" style={{marginTop:16}}>
    <section className="card"><h2>Add contribution</h2><label>Amount (KES)<input type="number" min="0.01" step="0.01" value={amount} onChange={e=>setAmount(e.target.value)} /></label><label>Source<select value={source} onChange={e=>setSource(e.target.value)}><option>MANUAL</option><option>MPESA</option><option>BANK</option><option>EMPLOYER</option><option>PAYER</option><option>REFUND</option></select></label><label>Reference<input value={reference} onChange={e=>setReference(e.target.value)} placeholder="External payment reference (optional)" /></label><button className="button" onClick={()=>void contribute()}>Record contribution</button></section>
    <section className="card"><h2>Apply to invoice</h2><label>Invoice ID<input value={invoiceId} onChange={e=>setInvoiceId(e.target.value)} placeholder="Invoice UUID" /></label><label>Amount (KES)<input type="number" min="0.01" step="0.01" value={applyAmount} onChange={e=>setApplyAmount(e.target.value)} /></label><label>Reference<input value={applyRef} onChange={e=>setApplyRef(e.target.value)} placeholder="Application reference (optional)" /></label><button className="button" onClick={()=>void apply()}>Apply wallet funds</button></section>
   </div>
   <section className="card" style={{marginTop:16}}><div className="card-header"><div><h2>Financial ledger</h2><p className="muted small">{wallet.transaction_count} recent transaction(s)</p></div><strong>{wallet.status}</strong></div>
    {wallet.transactions.length?<div className="table-wrap"><table><thead><tr><th>Date</th><th>Type</th><th>Reference</th><th>Source</th><th>Amount</th></tr></thead><tbody>{wallet.transactions.map(t=><tr key={t.id}><td>{t.created_at?new Date(t.created_at).toLocaleString():"—"}</td><td>{t.transaction_type}</td><td>{t.reference}</td><td>{t.source_type}</td><td>{t.direction==="CREDIT"?"+":"−"}{money(t.amount)}</td></tr>)}</tbody></table></div>:<p className="muted">No wallet transactions yet.</p>}
   </section>
   <div className="info-box" style={{marginTop:16}}><strong>Financial integrity:</strong> wallet balance is derived from append-only ledger transactions. Contributions are idempotent by wallet/reference, invoice applications cannot exceed available wallet funds or the outstanding patient amount, and mutations are audited.</div>
  </>}
 </div>;
}
