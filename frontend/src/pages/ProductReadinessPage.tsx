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
      <p className="muted">PHASE 125 · CAPABILITY & DEPENDENCY CONTROL</p>
      <h1>AfyaSync Product Readiness</h1>
      <p className="muted">Evidence control for the facility operating system: clinical care, cash operations, multi-payer financing, offline continuity, interoperability, security and external integration readiness.</p>
    </div></div>
    {error&&<div className="card"><p className="error" role="alert">{error}</p></div>}
    {loading?<div className="card">Checking readiness…</div>:data&&<>
      <div className="card" style={{marginBottom:18}}>
        <h2 style={{marginTop:0}}>Software release gate: {data.release_gate}</h2>
        <p>{data.software_readiness}</p>
        {data.blockers?.length>0&&<div><strong>Internal blockers</strong><ul>{data.blockers.map((b:string)=><li key={b}>{b}</li>)}</ul></div>}
      </div>

      <div className="card" style={{marginBottom:18}}>
        <h2 style={{marginTop:0}}>Independence & integration posture</h2>
        <div className="card-grid">
          <Metric label="SHA mode" value={data.integration_posture?.sha_mode||"UNKNOWN"} />
          <Metric label="SHA live ready" value={data.integration_posture?.sha_live_ready ? "YES" : "NO"} />
          <Metric label="Core cash requires SHA" value={data.integration_posture?.sha_is_required_for_core_cash ? "YES" : "NO"} />
          <Metric label="Offline queue" value={data.integration_posture?.offline_queue_available ? "AVAILABLE" : "NOT VERIFIED"} />
          <Metric label="HIE module" value={data.integration_posture?.hie_module_available ? "AVAILABLE" : "NOT VERIFIED"} />
        </div>
        <p className="muted small">{data.integration_posture?.note}</p>
      </div>

      <div className="card" style={{marginBottom:18}}>
        <h2 style={{marginTop:0}}>Capability control matrix</h2>
        <p className="muted">“IMPLEMENTED” means the corresponding application module is present and importable. It does not mean DHA certification, production credentials, or external approval has been granted.</p>
        <div className="table-wrap"><table><thead><tr><th>Capability</th><th>Status</th><th>Implementation evidence</th></tr></thead><tbody>
          {Object.entries(data.capability_matrix||{}).map(([key,value]:any)=><tr key={key}><td>{key.replaceAll("_"," ")}</td><td><span className="status-pill">{value.status}</span></td><td className="muted small">{value.module}</td></tr>)}
        </tbody></table></div>
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
        <p className="muted small">These are external evidence, credential, testing or approval gates and are deliberately not represented as completed by software checks.</p>
      </div>
    </>}
  </section>;
}

function Metric({label,value}:{label:string;value:string}){
  return <article className="card"><p className="eyebrow">{label}</p><strong style={{fontSize:"1.45rem"}}>{value}</strong></article>;
}
