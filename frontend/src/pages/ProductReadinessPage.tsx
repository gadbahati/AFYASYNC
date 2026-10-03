import {useEffect,useState} from "react";
import {api} from "../api/client";

export default function ProductReadinessPage(){
  const [data,setData]=useState<any>(null);
  const [simulation,setSimulation]=useState<any>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");

  async function load(){
    setLoading(true);setError("");
    try{setData(await api.productReadiness());}catch(err:any){setError(err?.message||err?.code||"READINESS_LOAD_FAILED");}
    finally{setLoading(false);}
  }
  async function runSimulation(){
    setError("");
    try{setSimulation(await api.runEndToEndSimulation());}catch(err:any){setError(err?.message||err?.code||"SIMULATION_FAILED");}
  }
  useEffect(()=>{void load();},[]);

  return <section className="page">
    <div className="page-header"><div>
      <p className="muted">PHASE 124 · FINAL PRODUCT READINESS</p>
      <h1>National-Scale Product Readiness</h1>
      <p className="muted">Final software control gate across tenancy, continuity, audit, simulation and production hardening.</p>
    </div></div>
    {error&&<div className="card"><p className="error" role="alert">{error}</p></div>}
    {loading?<div className="card">Checking readiness…</div>:data&&<>
      <div className="card" style={{marginBottom:18}}>
        <h2 style={{marginTop:0}}>Release gate: {data.release_gate}</h2>
        <p>{data.software_readiness}</p>
        {data.blockers?.length>0&&<div><strong>Blockers</strong><ul>{data.blockers.map((b:string)=><li key={b}>{b}</li>)}</ul></div>}
      </div>
      <div className="card-grid">
        {Object.entries(data.evidence||{}).map(([key,value]:any)=><div className="card" key={key}>
          <h3 style={{textTransform:"capitalize"}}>{key.replaceAll("_"," ")}</h3>
          <strong>{value.overall||value.band||"CHECKED"}</strong>
          <p className="muted small">{value.failed_checks?.length||value.failed_stages?.length||0} unresolved checks/stages</p>
        </div>)}
      </div>
      <div className="card" style={{marginTop:18}}>
        <h2>End-to-end simulation</h2>
        <button type="button" onClick={runSimulation}>Run non-destructive simulation</button>
        {simulation&&<pre style={{whiteSpace:"pre-wrap",marginTop:14}}>{JSON.stringify(simulation,null,2)}</pre>}
      </div>
      <div className="card" style={{marginTop:18}}>
        <h2>External gates</h2>
        <ul>{(data.external_gates||[]).map((x:string)=><li key={x}>{x}</li>)}</ul>
        <p className="muted small">These remain external evidence/approval gates and are deliberately not represented as completed by software checks.</p>
      </div>
    </>}
  </section>;
}
