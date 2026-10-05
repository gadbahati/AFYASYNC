import { useEffect, useState } from "react";
import { api } from "../api/client";

type Node = { id: string; code: string; name: string; node_type: string; trust_level: string; status: string };

export function SharedHealthRecordPage() {
  const [patientId, setPatientId] = useState("");
  const [nodes, setNodes] = useState<Node[]>([]);
  const [nodeId, setNodeId] = useState("");
  const [source, setSource] = useState<"LOCAL" | "HIE">("HIE");
  const [summary, setSummary] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [delivery, setDelivery] = useState<any>(null);

  useEffect(() => {
    void api.hieTrustedNodes().then((value: any) => setNodes(Array.isArray(value) ? value : [])).catch((e: unknown) => setError(e instanceof Error ? e.message : "HIE_NODE_DISCOVERY_FAILED"));
  }, []);

  async function retrieve() {
    setError(""); setSummary(null); setDelivery(null);
    if (!patientId.trim()) { setError("Enter a patient ID."); return; }
    if (source === "HIE" && !nodeId) { setError("Select a trusted HIE source."); return; }
    setLoading(true);
    try {
      setSummary(await api.patientSummary(patientId.trim(), source, source === "HIE" ? nodeId : undefined));
    } catch (e) {
      setError(e instanceof Error ? e.message : "PATIENT_SUMMARY_RETRIEVAL_FAILED");
    } finally { setLoading(false); }
  }

  return <section className="page-stack">
    <div className="page-header">
      <div><p className="eyebrow">Phase 203 · Kenya Patient Summary</p><h1>Shared Health Record</h1><p className="muted">Retrieve a governed patient summary from AfyaSync or a trusted HIE source. External access is consent-controlled and audited.</p></div>
    </div>
    <div className="card">
      <div className="form-grid">
        <label>Patient ID<input value={patientId} onChange={e => setPatientId(e.target.value)} placeholder="Patient UUID" /></label>
        <label>Source<select value={source} onChange={e => { setSource(e.target.value as "LOCAL" | "HIE"); setSummary(null); }}><option value="HIE">Trusted HIE / Shared Health Record</option><option value="LOCAL">AfyaSync local record</option></select></label>
        {source === "HIE" && <label>Trusted source<select value={nodeId} onChange={e => setNodeId(e.target.value)}><option value="">Select source</option>{nodes.filter(n => n.status === "ACTIVE" && ["HIGH","NATIONAL"].includes(n.trust_level)).map(n => <option key={n.id} value={n.id}>{n.name} ({n.code})</option>)}</select></label>}
      </div>
      <div className="form-actions"><button className="primary" disabled={loading} onClick={() => void retrieve()}>{loading ? "Retrieving…" : "Retrieve patient summary"}</button></div>
      {error && <div className="error-banner" role="alert">{error}</div>}
    </div>
    {summary && <div className="card"><div className="form-actions"><button className="secondary" disabled={loading || !patientId || !nodeId} onClick={async () => { setError(""); setDelivery(null); try { setDelivery(await api.deliverPatientSummary(patientId.trim(), nodeId)); } catch (e) { setError(e instanceof Error ? e.message : "PATIENT_SUMMARY_DELIVERY_FAILED"); } }}>Queue governed delivery to selected HIE source</button></div>{delivery && <p className="muted">Delivery queued: {delivery.id} · {delivery.status}</p>}</div>{summary && <div className="card"><div className="card-header"><div><p className="eyebrow">FHIR R4 document</p><h2>Patient Summary retrieved</h2><p className="muted">{summary.entry?.length ?? 0} resources · {summary.type ?? "unknown"} bundle</p></div><span className="status-badge">AUDITED</span></div><pre style={{whiteSpace:"pre-wrap",overflowX:"auto"}}>{JSON.stringify(summary, null, 2)}</pre></div>}
  </section>;
}
