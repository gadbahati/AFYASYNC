import {useEffect,useState} from "react";
import {useNavigate} from "react-router-dom";
import {useAuth} from "../auth/AuthContext";
import {useWorkspace} from "../workspaces/WorkspaceContext";
import {api} from "../api/client";
import {WORKSPACES} from "../workspaces/workspaces";

type ScopeSummary = {
  scope?: string;
  facility_count?: number;
  counts?: { patients?: number; encounters?: number; claims?: number };
  facilities?: { id: string; name: string; county?: string | null }[];
};

type OpsSummary = {
  metrics?: {
    patients?: number;
    encounters?: number;
    charges_total?: string;
    invoices_total?: string;
    confirmed_payments?: string;
    claims?: number;
    claims_amount?: string;
    claims_approved?: string;
    claims_paid?: string;
  };
  start_date?: string;
  end_date?: string;
};

export default function WorkspaceHomePage(){
  const auth=useAuth();
  const {workspace,setWorkspace,scope,setScope}=useWorkspace();
  const navigate=useNavigate();
  const current=WORKSPACES.find(w=>w.id===workspace)!;
  const [availableScopes,setAvailableScopes]=useState<string[]>(["facility"]);
  const [roles,setRoles]=useState<string[]>([]);
  const [permissions,setPermissions]=useState<string[]>([]);
  const [allowedWorkspaces,setAllowedWorkspaces]=useState<string[]>(["operations"]);
  const [summary,setSummary]=useState<ScopeSummary|null>(null);
  const [ops,setOps]=useState<OpsSummary|null>(null);
  const [summaryError,setSummaryError]=useState<string|null>(null);
  const [summaryLoading,setSummaryLoading]=useState(false);

  useEffect(()=>{
    api.contextOverview(scope).then((v:any)=>{
      setAvailableScopes(Array.isArray(v?.available_scopes)?v.available_scopes:["facility"]);
      setRoles(Array.isArray(v?.roles)?v.roles:[]);
      setPermissions(Array.isArray(v?.permissions)?v.permissions:[]);
      setAllowedWorkspaces(Array.isArray(v?.allowed_workspaces)?v.allowed_workspaces:["operations"]);
    }).catch(()=>setAvailableScopes(["facility"]));
  },[scope]);

  useEffect(()=>{
    let cancelled=false;
    setSummaryLoading(true);
    setSummaryError(null);
    Promise.all([
      api.contextScopeSummary(scope),
      api.contextOperationsSummary(scope).catch(()=>null),
    ]).then(([scopeSummary, opsSummary])=>{
      if(cancelled) return;
      setSummary(scopeSummary||null);
      setOps(opsSummary||null);
    }).catch((err:any)=>{
      if(!cancelled) setSummaryError(err?.message || err?.code || "SCOPE_SUMMARY_FAILED");
    }).finally(()=>{ if(!cancelled) setSummaryLoading(false); });
    return ()=>{ cancelled=true; };
  },[scope]);

  const visible=WORKSPACES.filter(w=>allowedWorkspaces.includes(w.id));
  const m=ops?.metrics;

  return <section className="page">
    <div className="page-header"><div>
      <p className="muted" style={{marginBottom:6}}>AFYASYNC WORKSPACE</p>
      <h1>{auth.facilityName||"Health workspace"}</h1>
      <p className="muted">Choose what you want to work on. Your access remains controlled by your authenticated permissions.</p>
    </div></div>

    <div className="card" style={{marginBottom:18}}>
      <h2 style={{marginTop:0}}>Operating context</h2>
      <p className="muted">This changes which facilities the platform may aggregate. Ordinary staff stay at facility/network; county and national require explicit authorization.</p>
      <select value={scope} onChange={(e)=>setScope(e.target.value as typeof scope)} style={{padding:"10px 12px",minWidth:240,borderRadius:8,border:"1px solid #cbd5e1",background:"#fff"}}>
        <option value="facility">Facility</option>
        <option value="network" disabled={!availableScopes.includes("network")}>Network{availableScopes.includes("network")?"":" — restricted"}</option>
        <option value="county" disabled={!availableScopes.includes("county")}>County{availableScopes.includes("county")?"":" — restricted"}</option>
        <option value="national" disabled={!availableScopes.includes("national")}>National{availableScopes.includes("national")?"":" — restricted"}</option>
      </select>
    </div>

    <div className="card" style={{marginBottom:18}}>
      <div style={{display:"flex",justifyContent:"space-between",gap:16,flexWrap:"wrap"}}>
        <div>
          <strong>Authorized operating profile</strong>
          <p className="muted" style={{margin:"6px 0 0"}}>{roles.length?roles.join(" • "):"Authenticated staff"}</p>
        </div>
        <div>
          <span className="muted">Available scopes: </span>
          <strong>{availableScopes.join(" • ")}</strong>
          <span className="muted" style={{display:"block",marginTop:6}}>{permissions.length} effective permissions</span>
        </div>
      </div>
    </div>

    <div className="card" style={{marginBottom:18}}>
      <h2 style={{marginTop:0}}>Data under this scope</h2>
      <p className="muted">Live aggregates limited to facilities authorized for <strong>{scope}</strong>{ops?.start_date ? ` · ${ops.start_date} → ${ops.end_date}` : ""}.</p>
      {summaryLoading && <p className="muted">Resolving authorized facilities…</p>}
      {summaryError && <div className="error" role="alert">{summaryError}</div>}
      {summary && !summaryLoading && (
        <>
          <div className="stat-grid" style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(140px,1fr))",gap:12,marginTop:12}}>
            <div className="stat-card"><div className="muted small">Facilities</div><div className="stat-value">{summary.facility_count ?? 0}</div></div>
            <div className="stat-card"><div className="muted small">Patients</div><div className="stat-value">{m?.patients ?? summary.counts?.patients ?? 0}</div></div>
            <div className="stat-card"><div className="muted small">Encounters</div><div className="stat-value">{m?.encounters ?? summary.counts?.encounters ?? 0}</div></div>
            <div className="stat-card"><div className="muted small">Claims</div><div className="stat-value">{m?.claims ?? summary.counts?.claims ?? 0}</div></div>
            <div className="stat-card"><div className="muted small">Charges (KES)</div><div className="stat-value">{m?.charges_total ?? "—"}</div></div>
            <div className="stat-card"><div className="muted small">Invoices (KES)</div><div className="stat-value">{m?.invoices_total ?? "—"}</div></div>
            <div className="stat-card"><div className="muted small">Payments (KES)</div><div className="stat-value">{m?.confirmed_payments ?? "—"}</div></div>
            <div className="stat-card"><div className="muted small">Claims paid (KES)</div><div className="stat-value">{m?.claims_paid ?? "—"}</div></div>
          </div>
          {Array.isArray(summary.facilities) && summary.facilities.length > 0 && (
            <div className="table-wrap" style={{marginTop:14}}>
              <table>
                <thead><tr><th>Facility</th><th>County</th></tr></thead>
                <tbody>
                  {summary.facilities.slice(0,12).map(f=>(
                    <tr key={f.id}><td>{f.name}</td><td>{f.county || "—"}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>

    <div className="card-grid">{visible.map(w=>(
      <button key={w.id} type="button" className="card" onClick={()=>{setWorkspace(w.id);navigate(w.links[0][0])}} style={{textAlign:"left",cursor:"pointer",border:workspace===w.id?"2px solid #0f766e":"1px solid #e2e8f0",background:"#fff"}}>
        <div style={{fontSize:30}}>{w.icon}</div>
        <h2 style={{margin:"8px 0 5px"}}>{w.label}</h2>
        <p className="muted" style={{margin:0}}>{w.description}</p>
      </button>
    ))}</div>

    <div className="card" style={{marginTop:18}}>
      <h2>{current.icon} {current.label}</h2>
      <p className="muted">{current.description}</p>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(220px,1fr))",gap:10}}>
        {current.links.map(([to,label])=>(
          <button key={to} type="button" onClick={()=>navigate(to)} style={{textAlign:"left",padding:14,border:"1px solid #e2e8f0",borderRadius:8,background:"#fff",cursor:"pointer"}}>
            {label}<span style={{float:"right"}}>→</span>
          </button>
        ))}
      </div>
    </div>
  </section>;
}
