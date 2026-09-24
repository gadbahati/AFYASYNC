import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

type Sop={id:string;title:string;audience?:string[];purpose?:string;steps?:string[];owner?:string};
type Mod={id:string;title:string;audience?:string[];duration?:string;objectives?:string[];lessons?:string[]};
type Help={id:string;q:string;a:string;category?:string};

export function TrainingPage(){
 const [sops,setSops]=useState<Sop[]>([]),[mods,setMods]=useState<Mod[]>([]),[help,setHelp]=useState<Help[]>([]);
 const [q,setQ]=useState(""),[audience,setAudience]=useState(""),[loading,setLoading]=useState(true),[error,setError]=useState("");
 const [tab,setTab]=useState<"sops"|"modules"|"help">("sops");
 const load=useCallback(async()=>{setLoading(true);setError("");try{const [s,m,h]=await Promise.all([api.trainingSops(audience),api.trainingModules(),api.trainingHelp(q)]);setSops(s.sops||[]);setMods(m.modules||[]);setHelp(h.topics||[])}catch(e:any){setError(e?.message||"Training content could not be loaded")}finally{setLoading(false)}},[audience,q]);
 useEffect(()=>{const t=setTimeout(()=>void load(),250);return()=>clearTimeout(t)},[load]);
 return <section className="page-stack">
  <div className="page-heading"><div><span className="eyebrow">TRAINING & SUPPORT</span><h1>Training, SOPs & help</h1><p className="muted">Give facility teams one place to learn AfyaSync workflows, follow standard operating procedures, and find operational answers.</p></div><button onClick={()=>void load()} disabled={loading}>{loading?"Refreshing…":"Refresh"}</button></div>
  {error&&<div className="warning-box">{error}</div>}
  <div className="card"><div className="row-between"><div><span className="eyebrow">CONTENT LIBRARY</span><h2>Find guidance</h2></div><span className="muted">{sops.length} SOPs · {mods.length} modules · {help.length} help topics</span></div>
   <div className="form-grid"><label>Audience<select value={audience} onChange={e=>setAudience(e.target.value)}><option value="">All teams</option><option value="clinical">Clinical</option><option value="nursing">Nursing</option><option value="laboratory">Laboratory</option><option value="pharmacy">Pharmacy</option><option value="billing">Billing</option><option value="administration">Administration</option></select></label><label>Search help<input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search a question or answer"/></label></div>
  </div>
  <div className="row-between"><div className="button-row"><button className={tab==="sops"?"":"secondary"} onClick={()=>setTab("sops")}>SOPs</button><button className={tab==="modules"?"":"secondary"} onClick={()=>setTab("modules")}>Training modules</button><button className={tab==="help"?"":"secondary"} onClick={()=>setTab("help")}>Help</button></div></div>
  {tab==="sops"&&<div className="card-grid">{sops.map(s=><article className="card" key={s.id}><span className="eyebrow">{s.id}</span><h2>{s.title}</h2><p className="muted">{s.purpose||"Standard operating procedure for facility teams."}</p><p className="small muted">{(s.audience||[]).join(" · ")}</p>{s.steps&&<ol>{s.steps.map((x,i)=><li key={i}>{x}</li>)}</ol>}</article>)}</div>}
  {tab==="modules"&&<div className="card-grid">{mods.map(m=><article className="card" key={m.id}><span className="eyebrow">{m.id}</span><h2>{m.title}</h2><p className="muted">{m.duration||"Self-paced"}</p><p className="small">{(m.audience||[]).join(" · ")}</p>{(m.objectives||m.lessons)&&<><h3>Learning points</h3><ul>{(m.objectives||m.lessons||[]).map((x,i)=><li key={i}>{x}</li>)}</ul></>}</article>)}</div>}
  {tab==="help"&&<div className="card"><div className="table-wrap"><table><thead><tr><th>Question</th><th>Answer</th></tr></thead><tbody>{help.map(h=><tr key={h.id}><td><strong>{h.q}</strong><div className="small muted">{h.category||""}</div></td><td>{h.a}</td></tr>)}</tbody></table></div></div>}
 </section>
}