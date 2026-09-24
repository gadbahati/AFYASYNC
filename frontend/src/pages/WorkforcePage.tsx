import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

type Staff={id:string;employee_number:string;professional_number?:string|null;department_id?:string|null;status:string};
type Compliance={active_staff:number;credentials_on_file:number;staff_without_credential:number;expired_count:number;expiring_within_days:number;expiring_count:number;missing:any[];expired:any[];expiring:any[];generated_at:string};
type Check={staff_id:string;employee_number:string;decision:string;credential_count:number;active:number;expired:number;blocked:number;credentials:any[]};

export function WorkforcePage(){
 const [staff,setStaff]=useState<Staff[]>([]),[total,setTotal]=useState(0),[compliance,setCompliance]=useState<Compliance|null>(null);
 const [selected,setSelected]=useState<Check|null>(null),[days,setDays]=useState(60),[loading,setLoading]=useState(true),[error,setError]=useState("");
 const [staffId,setStaffId]=useState(""),[council,setCouncil]=useState("KMPDC"),[cadre,setCadre]=useState(""),[licence,setLicence]=useState(""),[expiry,setExpiry]=useState(""),[notes,setNotes]=useState("");
 const load=useCallback(async()=>{setLoading(true);setError("");try{const [s,c]=await Promise.all([api.staffList(200,0,"ACTIVE"),api.workforceCompliance(days)]);setStaff(s.items||[]);setTotal(s.total||0);setCompliance(c)}catch(e:any){setError(e?.message||"Workforce data could not be loaded")}finally{setLoading(false)}},[days]);
 useEffect(()=>{void load()},[load]);
 const chosen=useMemo(()=>staff.find(s=>s.id===staffId),[staff,staffId]);
 async function check(id:string){try{setSelected(await api.workforceStaffCheck(id));setStaffId(id)}catch(e:any){setError(e?.message||"Credential check failed")}}
 async function register(e:React.FormEvent){e.preventDefault();if(!staffId){setError("Select a staff member first.");return}try{await api.workforceCredentialCreate({staff_id:staffId,council_code:council,cadre,licence_number:licence,issued_on:null,expiry_date:expiry||null,notes:notes||null});setCadre("");setLicence("");setExpiry("");setNotes("");await load();await check(staffId)}catch(e:any){setError(e?.message||"Credential registration failed")}}
 return <section className="page-stack">
  <div className="page-heading"><div><span className="eyebrow">WORKFORCE COMPLIANCE</span><h1>Workforce & credentials</h1><p className="muted">Track professional credentials and identify missing, expired or soon-to-expire licences for the current facility.</p></div><button onClick={()=>void load()} disabled={loading}>{loading?"Refreshing…":"Refresh"}</button></div>
  {error&&<div className="warning-box">{error}</div>}
  <div className="card-grid">
   <article className="card"><span className="eyebrow">ACTIVE STAFF</span><strong className="stat-value">{compliance?.active_staff??total}</strong></article>
   <article className="card"><span className="eyebrow">CREDENTIALS</span><strong className="stat-value">{compliance?.credentials_on_file??"—"}</strong></article>
   <article className="card"><span className="eyebrow">MISSING</span><strong className="stat-value">{compliance?.staff_without_credential??"—"}</strong></article>
   <article className="card"><span className="eyebrow">EXPIRED / EXPIRING</span><strong className="stat-value">{(compliance?.expired_count??0)+" / "+(compliance?.expiring_count??0)}</strong></article>
  </div>
  <div className="card-grid">
   <article className="card span-2"><div className="row-between"><div><span className="eyebrow">FACILITY COMPLIANCE</span><h2>Credential exceptions</h2></div><label className="small muted">Horizon <select value={days} onChange={e=>setDays(Number(e.target.value))}><option value={30}>30 days</option><option value={60}>60 days</option><option value={90}>90 days</option><option value={180}>180 days</option></select></label></div>
    <div className="table-wrap"><table><thead><tr><th>Employee</th><th>Issue</th><th>Licence</th><th>Expiry</th></tr></thead><tbody>
    {(compliance?.missing||[]).map((x:any)=><tr key={"m"+x.staff_id}><td>{x.employee_number}</td><td><span className="status-pill warning">MISSING</span></td><td>—</td><td>—</td></tr>)}
    {(compliance?.expired||[]).map((x:any)=><tr key={"e"+x.staff_id+x.licence_number}><td>{x.employee_number}</td><td><span className="status-pill warning">EXPIRED</span></td><td>{x.licence_number}</td><td>{x.expiry_date||"—"}</td></tr>)}
    {(compliance?.expiring||[]).map((x:any)=><tr key={"x"+x.staff_id+x.licence_number}><td>{x.employee_number}</td><td><span className="status-pill">EXPIRING</span></td><td>{x.licence_number}</td><td>{x.expiry_date}</td></tr>)}
    </tbody></table></div>
   </article>
   <article className="card"><span className="eyebrow">REGISTER</span><h2>Add credential</h2><form onSubmit={register} className="form-stack">
    <label>Staff<select value={staffId} onChange={e=>{setStaffId(e.target.value);if(e.target.value)void check(e.target.value)}}><option value="">Select staff</option>{staff.map(s=><option key={s.id} value={s.id}>{s.employee_number}</option>)}</select></label>
    <label>Council<select value={council} onChange={e=>setCouncil(e.target.value)}><option>KMPDC</option><option>NCK</option><option>PPB</option><option>COC</option><option>OTHER</option></select></label>
    <label>Cadre<input value={cadre} onChange={e=>setCadre(e.target.value)} required placeholder="e.g. Medical Officer"/></label>
    <label>Licence number<input value={licence} onChange={e=>setLicence(e.target.value)} required/></label>
    <label>Expiry date<input type="date" value={expiry} onChange={e=>setExpiry(e.target.value)}/></label>
    <label>Notes<input value={notes} onChange={e=>setNotes(e.target.value)}/></label>
    <button type="submit">Save credential</button></form>
   </article>
  </div>
  <article className="card"><div className="row-between"><div><span className="eyebrow">STAFF DIRECTORY</span><h2>Active workforce</h2></div><span className="muted">{total} staff</span></div>
   <div className="table-wrap"><table><thead><tr><th>Employee</th><th>Professional no.</th><th>Department</th><th>Status</th><th>Credential check</th></tr></thead><tbody>{staff.map(s=><tr key={s.id}><td><strong>{s.employee_number}</strong></td><td>{s.professional_number||"—"}</td><td>{s.department_id||"—"}</td><td>{s.status}</td><td><button type="button" onClick={()=>void check(s.id)}>Check</button></td></tr>)}</tbody></table></div>
  </article>
  {selected&&<article className="card"><div className="row-between"><div><span className="eyebrow">CREDENTIAL CHECK</span><h2>{selected.employee_number}</h2></div><span className={"status-pill"+(selected.decision==="CLEAR"?"":" warning")}>{selected.decision}</span></div>
   <div className="card-grid"><div><strong>{selected.active}</strong><span className="muted"> active</span></div><div><strong>{selected.expired}</strong><span className="muted"> expired</span></div><div><strong>{selected.blocked}</strong><span className="muted"> blocked</span></div></div>
   <div className="table-wrap"><table><thead><tr><th>Council</th><th>Licence</th><th>Cadre</th><th>Status</th><th>Expiry</th></tr></thead><tbody>{selected.credentials.map(c=><tr key={c.id}><td>{c.council_code}</td><td>{c.licence_number}</td><td>{c.cadre}</td><td>{c.status}</td><td>{c.expiry_date||"—"}</td></tr>)}</tbody></table></div>
  </article>}
 </section>
}