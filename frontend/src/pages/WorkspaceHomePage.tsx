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
  const {workspace,setWorkspace,scope,setScope,tenantId,setTenantId}=useWorkspace();
  const navigate=useNavigate();
  const current=WORKSPACES.find(w=>w.id===workspace)!;
  const [availableScopes,setAvailableScopes]=useState<string[]>(["facility"]);
  const [roles,setRoles]=useState<string[]>([]);
  const [permissions,setPermissions]=useState<string[]>([]);
  const [allowedWorkspaces,setAllowedWorkspaces]=useState<string[]>(["operations"]);
  const [allowedPaths,setAllowedPaths]=useState<string[]|null>(null);
  const [tenants,setTenants]=useState<any[]>([]);
  const [tenantError,setTenantError]=useState<string|null>(null);
  const [summary,setSummary]=useState<ScopeSummary|null>(null);
  const [ops,setOps]=useState<OpsSummary|null>(null);
  const [summaryError,setSummaryError]=useState<string|null>(null);
  const [summaryLoading,setSummaryLoading]=useState(false);
  const [scopeBusy,setScopeBusy]=useState(false);
  const [scopeError,setScopeError]=useState<string|null>(null);

  useEffect(()=>{
    api.tenancyOverview().then((v:any)=>{
      const list=Array.isArray(v?.organizations)?v.organizations:[];
      setTenants(list);
      if(!tenantId && list.length) setTenantId(list[0].id);
    }).catch(()=>setTenants([]));
  },[]);
  
  useEffect(()=>{
    api.contextOverview(scope,tenantId).then((v:any)=>{
      setAvailableScopes(Array.isArray(v?.available_scopes)?v.available_scopes:["facility"]);
      setRoles(Array.isArray(v?.roles)?v.roles:[]);
      setPermissions(Array.isArray(v?.permissions)?v.permissions:[]);
      setAllowedWorkspaces(Array.isArray(v?.allowed_workspaces)?v.allowed_workspaces:["operations"]);
      const paths = v?.module_actions?.allowed_paths;
      setAllowedPaths(Array.isArray(paths) ? paths : null);
    }).catch(()=>setAvailableScopes(["facility"]));
  },[scope,tenantId]);

  useEffect(()=>{
    let cancelled=false;
    setSummaryLoading(true);
    setSummaryError(null);
    Promise.all([
      api.contextScopeSummary(scope,tenantId),
      api.contextOperationsSummary(scope,undefined,undefined,tenantId).catch(()=>null),
    ]).then(([scopeSummary, opsSummary])=>{
      if(cancelled) return;
      setSummary(scopeSummary||null);
      setOps(opsSummary||null);
    }).catch((err:any)=>{
      if(!cancelled) setSummaryError(err?.message || err?.code || "SCOPE_SUMMARY_FAILED");
    }).finally(()=>{ if(!cancelled) setSummaryLoading(false); });
    return ()=>{ cancelled=true; };
  },[scope,tenantId]);

  function scopePathAllowed(to: string): boolean {
    const path = to.split("?")[0] || "/";
    if (scope === "facility") {
      return !path.startsWith("/national") &&
        !path.startsWith("/coverage-simulator") &&
        !path.startsWith("/universal-identity") &&
        !path.startsWith("/health-exchange") &&
        !path.startsWith("/provider-network");
    }
    if (scope === "network") {
      return !path.startsWith("/national-command-centre") &&
        !path.startsWith("/national-intelligence") &&
        !path.startsWith("/national-identity") &&
        !path.startsWith("/national-facilities") &&
        !path.startsWith("/national-staff") &&
        !path.startsWith("/national-payers") &&
        !path.startsWith("/national-benefits") &&
        !path.startsWith("/national-financing") &&
        !path.startsWith("/national-supply") &&
        !path.startsWith("/national/") &&
        !path.startsWith("/coverage-simulator");
    }
    if (scope === "county") {
      return !path.startsWith("/national-identity") &&
        !path.startsWith("/national-facilities") &&
        !path.startsWith("/national-staff") &&
        !path.startsWith("/national-payers") &&
        !path.startsWith("/national-benefits") &&
        !path.startsWith("/national-financing") &&
        !path.startsWith("/universal-identity");
    }
    return true;
  }

  const visible=WORKSPACES.filter(w=>
    allowedWorkspaces.includes(w.id) &&
    w.links.some(([to])=>scopePathAllowed(to) && pathAllowed(to))
  );

  function pathAllowed(to: string): boolean {
    if (allowedPaths === null) return true;
    const path = to.split("?")[0] || "/";
    return allowedPaths.some((p) => {
      if (p === "/") return path === "/";
      return path === p || path.startsWith(p + "/");
    });
  }
  const workspaceLinks = current.links.filter(([to]) => scopePathAllowed(to) && pathAllowed(to));
  const m=ops?.metrics;

  return <section className="page">
    <div className="page-header"><div>
      <p className="muted" style={{marginBottom:6}}>AFYASYNC WORKSPACE</p>
      <h1>{auth.facilityName||"Health workspace"}</h1>
      <p className="muted">Choose what you want to work on. Your access remains controlled by your authenticated permissions.</p>
    </div></div>

    <div className="card" style={{marginBottom:18}}>
      <h2 style={{marginTop:0}}>Organization / tenant</h2>
      <p className="muted">Choose the authorized organization boundary before selecting a broader operating scope.</p>
      <select value={tenantId || ""} onChange={async(e)=>{
        const id=e.target.value || null;
        setTenantError(null);
        if(!id){setTenantId(null);return;}
        try{await api.tenancySelect(id);setTenantId(id);}catch(err:any){setTenantError(err?.message||err?.code||"TENANT_SELECTION_DENIED");}
      }} style={{padding:"10px 12px",minWidth:320,borderRadius:8,border:"1px solid #cbd5e1",background:"#fff"}}>
        <option value="">Select authorized organization</option>
        {tenants.map(t=><option key={t.id} value={t.id}>{t.name} — {t.organization_type} ({t.facility_count})</option>)}
      </select>
      {tenantError && <p className="error" role="alert">{tenantError}</p>}
    </div>

    <div className="card" style={{marginBottom:18}}>
      <h2 style={{marginTop:0}}>Operating context</h2>
      <p className="muted">This changes which facilities the platform may aggregate. Ordinary staff stay at facility/network; county and national require explicit authorization.</p>
      <select value={scope} disabled={scopeBusy} onChange={async(e)=>{
        const next=e.target.value as typeof scope;
        if(next===scope || scopeBusy) return;
        setScopeBusy(true);
        setScopeError(null);
        try {
          await api.setOperatingScope(next,scope,tenantId);
          setScope(next);
          navigate("/workspace");
        } catch(err:any) {
          setScopeError(err?.message || err?.code || "SCOPE_NOT_AUTHORIZED");
        } finally {
          setScopeBusy(false);
        }
      }} style={{padding:"10px 12px",minWidth:240,borderRadius:8,border:"1px solid #cbd5e1",background:"#fff",cursor:scopeBusy?"wait":"pointer"}}>
        {["facility","network","county","national"].map(value=>(
          <option key={value} value={value} disabled={!availableScopes.includes(value)}>
            {value[0].toUpperCase()+value.slice(1)}{availableScopes.includes(value)?"":" — restricted"}
          </option>
        ))}
      </select>
      {scopeError && <p className="error" role="alert">{scopeError}</p>}
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
          {allowedPaths && (
            <span className="muted" style={{display:"block",marginTop:4}}>{allowedPaths.length} authorized module paths</span>
          )}
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
      <button key={w.id} type="button" className="card" onClick={()=>{setWorkspace(w.id); const first = w.links.find(([to]) => pathAllowed(to)); navigate((first?.[0]) || "/");}} style={{textAlign:"left",cursor:"pointer",border:workspace===w.id?"2px solid #0f766e":"1px solid #e2e8f0",background:"#fff"}}>
        <div style={{fontSize:30}}>{w.icon}</div>
        <h2 style={{margin:"8px 0 5px"}}>{w.label}</h2>
        <p className="muted" style={{margin:0}}>{w.description}</p>
      </button>
    ))}</div>

    <div className="card" style={{marginTop:18}}>
      <h2>{current.icon} {current.label}</h2>
      <p className="muted">{current.description}</p>
      {allowedPaths && workspaceLinks.length < current.links.length && (
        <p className="muted small">Some modules are hidden because your role does not include the required permissions.</p>
      )}
      {allowedPaths && workspaceLinks.length === 0 && (
        <p className="error" role="status">No modules available in this workspace for your permission set.</p>
      )}
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(220px,1fr))",gap:10}}>
        {workspaceLinks.map(([to,label])=>(
          <button key={to} type="button" onClick={()=>navigate(to)} style={{textAlign:"left",padding:14,border:"1px solid #e2e8f0",borderRadius:8,background:"#fff",cursor:"pointer"}}>
            {label}<span style={{float:"right"}}>→</span>
          </button>
        ))}
      </div>
    </div>
  </section>;
}
