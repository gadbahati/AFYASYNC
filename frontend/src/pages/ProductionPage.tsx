import { useCallback,useEffect,useState } from "react";
import { api } from "../api/client";

type Check={code:string;ok:boolean;detail:string;severity:string};
type Readiness={environment:string;is_production:boolean;band:string;score_pct:number;passed:number;total:number;checks:Check[];deploy_blocked:boolean;generated_at:string};
type Checklist={title:string;steps:Array<{id:string;step:string}>;env_template:Record<string,string>;note:string};

export function ProductionPage(){
 const [r,setR]=useState<Readiness|null>(null),[c,setC]=useState<Checklist|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState("");
 const load=useCallback(async()=>{setLoading(true);setError("");try{const [a,b]=await Promise.all([api.productionReadiness(),api.productionDeployChecklist()]);setR(a);setC(b)}catch(e){setError(e instanceof Error?e.message:"Unable to load production readiness")}finally{setLoading(false)}},[]);
 useEffect(()=>{void load()},[load]);
 return <section><div className="page-header"><div><div className="eyebrow">PHASE 31 • PRODUCTION HARDENING</div><h1>Production readiness</h1><p className="muted">Runtime safety checks, secrets hygiene and deployment controls.</p></div><button className="button secondary" onClick={()=>void load()} disabled={loading}>{loading?"Refreshing…":"Refresh"}</button></div>
 {error&&<div className="alert error">{error}</div>}
 {loading&&!r?<div className="card"><p>Loading production checks…</p></div>:r&&<><div className="grid grid-4"><div className="card stat"><span>Posture</span><strong>{r.band}</strong><small>{r.score_pct}% passed</small></div><div className="card stat"><span>Checks</span><strong>{r.passed}/{r.total}</strong><small>Current runtime</small></div><div className="card stat"><span>Environment</span><strong>{r.environment}</strong><small>{r.is_production?"Production":"Non-production"}</small></div><div className="card stat"><span>Deploy gate</span><strong>{r.deploy_blocked?"Blocked":"Open"}</strong><small>Critical failures</small></div></div>
 <div className="card"><div className="card-header"><div><h2>Runtime checks</h2><p className="muted">Secret values are never exposed.</p></div></div><div className="table-wrap"><table><thead><tr><th>Check</th><th>Severity</th><th>Status</th><th>Detail</th></tr></thead><tbody>{r.checks.map(x=><tr key={x.code}><td>{x.code}</td><td>{x.severity}</td><td><span className="badge">{x.ok?"PASS":"OPEN"}</span></td><td>{x.detail}</td></tr>)}</tbody></table></div></div>
 </>}
 {c&&<div className="grid grid-2"><div className="card"><div className="card-header"><div><h2>Deployment checklist</h2><p className="muted">Operational steps before production release.</p></div></div><div className="stack">{c.steps.map(s=><div className="list-row" key={s.id}><strong>{s.id}</strong><span>{s.step}</span></div>)}</div></div><div className="card"><div className="card-header"><div><h2>Environment template</h2><p className="muted">{c.note}</p></div></div><div className="stack">{Object.entries(c.env_template).map(([k,v])=><div className="list-row" key={k}><strong>{k}</strong><code>{v}</code></div>)}</div></div></div>}
 {r&&<p className="muted small">Generated {new Date(r.generated_at).toLocaleString()}.</p>}
 </section>
}