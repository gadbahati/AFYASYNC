import {useNavigate} from "react-router-dom";
import {useAuth} from "../auth/AuthContext";
import {useWorkspace} from "../workspaces/WorkspaceContext";
import {WORKSPACES} from "../workspaces/workspaces";
export default function WorkspaceHomePage(){
 const auth=useAuth();const {workspace,setWorkspace}=useWorkspace();const navigate=useNavigate();
 const current=WORKSPACES.find(w=>w.id===workspace)!;
 return <section className="page">
  <div className="page-header"><div><p className="muted" style={{marginBottom:6}}>AFYASYNC WORKSPACE</p><h1>{auth.facilityName||"Health workspace"}</h1><p className="muted">Choose what you want to work on. Your access remains controlled by your authenticated permissions.</p></div></div>
  <div className="card-grid">{WORKSPACES.map(w=><button key={w.id} type="button" className="card" onClick={()=>{setWorkspace(w.id);navigate(w.links[0][0])}} style={{textAlign:"left",cursor:"pointer",border:workspace===w.id?"2px solid #0f766e":"1px solid #e2e8f0"}}>
   <div style={{fontSize:30}}>{w.icon}</div><h2 style={{margin:"8px 0 5px"}}>{w.label}</h2><p className="muted" style={{margin:0}}>{w.description}</p>
  </button>)}</div>
  <div className="card" style={{marginTop:18}}><h2>{current.icon} {current.label}</h2><p className="muted">{current.description}</p><div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(220px,1fr))",gap:10}}>{current.links.map(([to,label])=><button key={to} type="button" onClick={()=>navigate(to)} style={{textAlign:"left",padding:14}}>{label}<span style={{float:"right"}}>→</span></button>)}</div></div>
 </section>
}
