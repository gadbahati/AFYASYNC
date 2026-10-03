import {useState} from "react";
import {api} from "../api/client";

export default function RevenueWorkflowAutomationPage(){
  const [limit,setLimit]=useState(50);
  const [result,setResult]=useState<any>(null);
  const [running,setRunning]=useState(false);
  async function run(){
    setRunning(true);
    try{setResult(await api.revenueWorkflowAutomate(limit));}
    finally{setRunning(false);}
  }
  return <section className="page">
    <div className="page-header"><div><h1>Revenue workflow automation</h1><p>Turn prioritized revenue issues into traceable collection work without creating duplicate active tasks.</p></div>
      <button className="primary" onClick={run} disabled={running}>{running?"Synchronizing…":"Automate revenue actions"}</button>
    </div>
    <div className="card-grid">
      <div className="card"><span className="muted">Batch limit</span><strong><input type="number" min={1} max={200} value={limit} onChange={e=>setLimit(Number(e.target.value)||50)} /></strong></div>
      <div className="card"><span className="muted">Created</span><strong>{result?.created ?? "—"}</strong></div>
      <div className="card"><span className="muted">Updated</span><strong>{result?.updated ?? "—"}</strong></div>
      <div className="card"><span className="muted">Skipped</span><strong>{result?.skipped ?? "—"}</strong></div>
    </div>
    <div className="card"><h2>Closed-loop workflow</h2><p>Revenue action priorities → collection work queue → assigned operational follow-up → resolution.</p><p className="muted">Automation is idempotent: an existing active work item is updated instead of duplicated. Each item retains its source type and source record ID.</p></div>
    {result && <div className="card"><h2>Last synchronization</h2><pre>{JSON.stringify(result,null,2)}</pre></div>}
  </section>
}
