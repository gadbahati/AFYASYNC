import { useEffect, useState } from "react";
import { api } from "../api/client";

type Data={window_days:number;guardrails:{open:number;amount_at_risk:number};collection_work:{open:number;outstanding:number};recovery:{open:number;outstanding:number};resolution:{open:number;amount_at_risk:number};total_exposure:number;operational_queue:number};

export default function ContractCashCommandPage(){
  const [data,setData]=useState<Data|null>(null); const [days,setDays]=useState(90); const [busy,setBusy]=useState(false);
  const load=async()=>{setBusy(true);try{const r=await api.contractCashCommand(days);setData(r)}finally{setBusy(false)}};
  useEffect(()=>{void load()},[days]);
  const money=(n:number)=>"KES "+Number(n||0).toLocaleString(undefined,{maximumFractionDigits:0});
  return <div className="page">
    <div className="page-header"><div><h1>Contract-to-Cash Command Centre</h1><p>Closed-loop visibility from contract enforcement to recovery and resolution.</p></div>
      <select value={days} onChange={e=>setDays(Number(e.target.value))}><option value={30}>30 days</option><option value={90}>90 days</option><option value={180}>180 days</option><option value={365}>365 days</option></select></div>
    {busy&&!data?<p>Loading command centre…</p>:data&&<>
      <div className="stat-grid">
        <div className="stat-card"><span>Open guardrails</span><strong>{data.guardrails.open}</strong><small>{money(data.guardrails.amount_at_risk)} at risk</small></div>
        <div className="stat-card"><span>Collection work</span><strong>{data.collection_work.open}</strong><small>{money(data.collection_work.outstanding)} outstanding</small></div>
        <div className="stat-card"><span>Recovery cases</span><strong>{data.recovery.open}</strong><small>{money(data.recovery.outstanding)} outstanding</small></div>
        <div className="stat-card"><span>Resolution cases</span><strong>{data.resolution.open}</strong><small>{money(data.resolution.amount_at_risk)} at risk</small></div>
      </div>
      <section className="card"><h2>Contract-to-cash exposure</h2><div className="command-total">{money(data.total_exposure)}</div><p>Combined operational exposure surfaced by contract compliance, recovery and resolution workflows. The figures are operational signals and may overlap across linked cases.</p>
      <div className="inline-actions"><a className="button" href="/contract-guardrails">Guardrails</a><a className="button" href="/collection-work">Collection work</a><a className="button" href="/revenue-recovery">Recovery</a><a className="button" href="/revenue-resolution">Resolution</a></div></section>
      <section className="card"><h2>Closed-loop operating model</h2><ol><li>Activated contract terms enforce tariff and claims rules.</li><li>Compliance guardrails identify tariff, adjudication and payment variances.</li><li>Guardrails become actionable collection work.</li><li>Settlement shortfalls enter revenue recovery.</li><li>Denials and unresolved financial cases continue through resolution and appeal workflows.</li></ol><strong>{data.operational_queue} active operational items</strong></section>
    </>}
  </div>
}
