import {useEffect, useState, type FormEvent} from "react";
import {api} from "../api/client";

type Tenant={id:string;code:string;name:string;organization_type:string;parent_id?:string|null;facility_count:number;status:string};

export default function TenancyPage(){
  const [tenants,setTenants]=useState<Tenant[]>([]);
  const [admin,setAdmin]=useState(false);
  const [name,setName]=useState("");
  const [code,setCode]=useState("");
  const [type,setType]=useState("PROVIDER_NETWORK");
  const [facilityId,setFacilityId]=useState("");
  const [selected,setSelected]=useState<string>("");
  const [message,setMessage]=useState("");
  const [error,setError]=useState("");

  async function load(){
    try{
      const v=await api.tenancyOverview();
      setTenants(Array.isArray(v?.organizations)?v.organizations:[]);
      setAdmin(Boolean(v?.tenant_admin));
    }catch(err:any){setError(err?.message||err?.code||"TENANCY_LOAD_FAILED");}
  }
  useEffect(()=>{void load();},[]);

  async function create(e:FormEvent){
    e.preventDefault();setError("");setMessage("");
    try{
      await api.tenancyCreateOrganization({code,name,organization_type:type});
      setName("");setCode("");setMessage("Organization created.");await load();
    }catch(err:any){setError(err?.message||err?.code||"TENANT_CREATE_FAILED");}
  }

  async function attachFacility(){
    setError("");setMessage("");
    if(!selected||!facilityId.trim()){setError("Select an organization and enter a facility ID.");return;}
    try{
      await api.tenancyAttachFacility(selected,facilityId.trim());
      setMessage("Facility attached to tenant.");await load();
    }catch(err:any){setError(err?.message||err?.code||"TENANT_FACILITY_ATTACH_FAILED");}
  }

  return <section className="page">
    <div className="page-header"><div>
      <p className="muted">PHASE 119 · MULTI-TENANT CONTROL PLANE</p>
      <h1>Organizations & tenant boundaries</h1>
      <p className="muted">Manage explicit organization membership without weakening facility-level authorization.</p>
    </div></div>

    {error&&<div className="card" style={{marginBottom:14}}><p className="error" role="alert">{error}</p></div>}
    {message&&<div className="card" style={{marginBottom:14}}><p>{message}</p></div>}

    {!admin&&<div className="card"><p>Your account can view its authorized tenant memberships, but tenant administration requires the dedicated tenancy administration capability.</p></div>}

    {admin&&<div className="card" style={{marginBottom:18}}>
      <h2>Create organization</h2>
      <form onSubmit={create} style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))",gap:10}}>
        <input value={name} onChange={e=>setName(e.target.value)} placeholder="Organization name" required />
        <input value={code} onChange={e=>setCode(e.target.value)} placeholder="Unique code" required />
        <select value={type} onChange={e=>setType(e.target.value)}>
          <option>PROVIDER_NETWORK</option><option>FACILITY_GROUP</option><option>COUNTY</option><option>NATIONAL</option><option>PARTNER</option>
        </select>
        <button type="submit">Create tenant</button>
      </form>
    </div>}

    <div className="card" style={{marginBottom:18}}>
      <h2>Attach facility</h2>
      <div style={{display:"grid",gridTemplateColumns:"minmax(220px,1fr) minmax(220px,1fr) auto",gap:10}}>
        <select value={selected} onChange={e=>setSelected(e.target.value)}>
          <option value="">Select organization</option>
          {tenants.map(t=><option key={t.id} value={t.id}>{t.name} — {t.organization_type}</option>)}
        </select>
        <input value={facilityId} onChange={e=>setFacilityId(e.target.value)} placeholder="Facility UUID" />
        <button type="button" onClick={attachFacility} disabled={!admin}>Attach</button>
      </div>
    </div>

    <div className="card">
      <h2>Authorized organizations</h2>
      <div className="table-wrap">
        <table><thead><tr><th>Name</th><th>Code</th><th>Type</th><th>Facilities</th><th>Status</th></tr></thead>
        <tbody>{tenants.map(t=><tr key={t.id}><td>{t.name}</td><td>{t.code}</td><td>{t.organization_type}</td><td>{t.facility_count}</td><td>{t.status}</td></tr>)}</tbody>
        </table>
      </div>
    </div>
  </section>;
}
