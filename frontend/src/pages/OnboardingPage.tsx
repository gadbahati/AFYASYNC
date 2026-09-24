import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

type Step = { code:string; label:string; done:boolean; value:any };
type Kit = { facility_id:string; facility_name?:string; county?:string; completion_pct:number; band:string; steps:Step[]; runbook:string[]; generated_at:string };
type Playbook = { title:string; phases:{name:string;items:string[]}[]; note:string; generated_at:string };

export function OnboardingPage() {
  const [kit,setKit]=useState<Kit|null>(null);
  const [playbook,setPlaybook]=useState<Playbook|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");

  const load=useCallback(async()=>{
    setLoading(true); setError("");
    try {
      const [k,p]=await Promise.all([api.onboardingFacilityKit(),api.onboardingMigrationPlaybook()]);
      setKit(k); setPlaybook(p);
    } catch(e:any) {
      setError(e?.message || "Onboarding readiness could not be loaded");
    } finally { setLoading(false); }
  },[]);

  useEffect(()=>{void load()},[load]);

  const done=kit?.steps.filter(s=>s.done).length ?? 0;
  const total=kit?.steps.length ?? 0;

  return <section className="page-stack">
    <div className="page-heading">
      <div>
        <span className="eyebrow">FACILITY ONBOARDING</span>
        <h1>Onboarding & migration</h1>
        <p className="muted">Prepare the current facility for AfyaSync go-live, identify missing readiness items, and follow the migration playbook.</p>
      </div>
      <button type="button" onClick={()=>void load()} disabled={loading}>{loading?"Refreshing…":"Refresh"}</button>
    </div>

    {error&&<div className="warning-box">{error}</div>}

    <div className="card-grid">
      <article className="card">
        <span className="eyebrow">FACILITY</span>
        <h2>{kit?.facility_name || "Current facility"}</h2>
        <p className="muted">{kit?.county || "County not supplied"}</p>
      </article>
      <article className="card">
        <span className="eyebrow">READINESS</span>
        <strong className="stat-value">{kit ? kit.completion_pct+"%" : "—"}</strong>
        <p className="muted">{done} of {total} checklist items complete</p>
      </article>
      <article className="card">
        <span className="eyebrow">READINESS BAND</span>
        <strong className={"status-pill"+(kit?.band==="GREEN"?"":" warning")}>{kit?.band || "—"}</strong>
        <p className="muted">Based on the facility onboarding checklist.</p>
      </article>
    </div>

    <div className="card-grid">
      <article className="card span-2">
        <div className="row-between"><div><span className="eyebrow">CHECKLIST</span><h2>Facility migration readiness</h2></div><span className="muted">{done}/{total}</span></div>
        <div className="table-wrap"><table><thead><tr><th>Readiness item</th><th>Value</th><th>Status</th></tr></thead><tbody>
          {(kit?.steps||[]).map(s=><tr key={s.code}><td><strong>{s.label}</strong></td><td>{String(s.value ?? "—")}</td><td><span className={"status-pill"+(s.done?"":" warning")}>{s.done?"READY":"ACTION REQUIRED"}</span></td></tr>)}
        </tbody></table></div>
      </article>
      <article className="card">
        <span className="eyebrow">GO-LIVE RUNBOOK</span>
        <h2>Next operational steps</h2>
        <ol>{(kit?.runbook||[]).map((item,i)=><li key={i}>{item.replace(/^\\d+\\.\\s*/,"")}</li>)}</ol>
      </article>
    </div>

    <article className="card">
      <div className="row-between"><div><span className="eyebrow">MIGRATION PLAYBOOK</span><h2>{playbook?.title || "Facility migration playbook"}</h2></div><span className="muted">Operational guidance</span></div>
      <div className="card-grid">
        {(playbook?.phases||[]).map(phase=><div className="card" key={phase.name}><span className="eyebrow">{phase.name}</span><ul>{phase.items.map((item,i)=><li key={i}>{item}</li>)}</ul></div>)}
      </div>
      {playbook?.note&&<p className="muted">{playbook.note}</p>}
    </article>

    {kit?.generated_at&&<p className="muted small">Readiness generated {new Date(kit.generated_at).toLocaleString()}.</p>}
  </section>;
}
