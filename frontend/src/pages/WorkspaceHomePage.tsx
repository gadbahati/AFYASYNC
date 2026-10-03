import {useEffect,useState} from "react";
import {useNavigate} from "react-router-dom";
import {useAuth} from "../auth/AuthContext";
import {useWorkspace} from "../workspaces/WorkspaceContext";
import {api} from "../api/client";
import {WORKSPACES} from "../workspaces/workspaces";
export default function WorkspaceHomePage(){
 const auth=useAuth();const {workspace,setWorkspace,scope,setScope}=useWorkspace();const navigate=useNavigate();
 const current=WORKSPACES.find(w=>w.id===workspace)!;
 const [availableScopes,setAvailableScopes]=useState<string[]>(["facility"]); const [roles,setRoles]=useState<string[]>([]); const [permissions,setPermissions]=useState<string[]>([]); const [allowedWorkspaces,setAllowedWorkspaces]=useState<string[]>(["operations"]);
 useEffect(()=>{api.contextOverview().then((v:any)=>setAvailableScopes(Array.isArray(v?.available_scopes)?v.available_scopes:["facility"]); setRoles(Array.isArray(v?.roles)?v.roles:[]); setPermissions(Array.isArray(v?.permissions)?v.permissions:[]); setAllowedWorkspaces(Array.isArray(v?.allowed_workspaces)?v.allowed_workspaces:["operations"])).catch(()=>setAvailableScopes(["facility"]));},[]);
 return <section className="page">
  <div className="page-header"><div><p className="muted" style={{marginBottom:6}}>AFYASYNC WORKSPACE</p><h1>{auth.facilityName||"Health workspace"}</h1><p className="muted">Choose what you want to work on. Your access remains controlled by your authenticated permissions.</p></div></div>
  <div className="card" style={{marginBottom:18}}><h2 style={{marginTop:0}}>Operating context</h2><p className="muted">Choose the level you are authorized to operate at. The same workspace changes its view according to this context.</p><select value={scope} onChange={(e)=>setScope(e.target.value as typeof scope)} style={{padding:"10px 12px",minWidth:240,borderRadius:8}}><option value="facility">Facility</option><option value="network" disabled={!availableScopes.includes("network")}>Network{availableScopes.includes("network")?"":" — restricted"}</option><option value="county" disabled={!availableScopes.includes("county")}>County{availableScopes.includes("county")?"":" — restricted"}</option><option value="national" disabled={!availableScopes.includes("national")}>National{availableScopes.includes("national")?"":" — restricted"}</option></select></div><div className="card" style={{marginBottom:18}}><div style={{display:"flex",justifyContent:"space-between",gap:16,flexWrap:"wrap"}}><div><strong>Authorized operating profile</strong><p className="muted" style={{margin:"6px 0 0"}}>{roles.length?roles.join(" • "):"Authenticated staff"}</p></div><div><span className="muted">Available scopes: </span><strong>{availableScopes.join(" • ")}</strong><span className="muted" style={{display:"block",marginTop:6}}>{permissions.length} effective permissions</span></div></div></div><div className="card-grid">{WORKSPACES.filter(w=>allowedWorkspaces.includes(w.id)).map(w=><button key={w.id} type="button" className="card" onClick={()=>{setWorkspace(w.id);navigate(w.links[0][0])}} style={{textAlign:"left",cursor:"pointer",border:workspace===w.id?"2px solid #0f766e":"1px solid #e2e8f0"}}>
   <div style={{fontSize:30}}>{w.icon}</div><h2 style={{margin:"8px 0 5px"}}>{w.label}</h2><p className="muted" style={{margin:0}}>{w.description}</p>
  </button>)}</div>
  <div className="card" style={{marginTop:18}}><h2>{current.icon} {current.label}</h2><p className="muted">{current.description}</p><div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(220px,1fr))",gap:10}}>{current.links.map(([to,label])=><button key={to} type="button" onClick={()=>navigate(to)} style={{textAlign:"left",padding:14}}>{label}<span style={{float:"right"}}>→</span></button>)}</div></div>
 </section>
}
