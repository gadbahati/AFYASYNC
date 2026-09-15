import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { Department, Encounter, LabOrderDetail, LabTest, Patient, Queue, QueueEntry } from "../api/types";
import "./lab.css";

type Priority = "NORMAL" | "URGENT" | "EMERGENCY";
type PatientMap = Record<string, Patient>;

export function LaboratoryWorkflowPage() {
  const [params] = useSearchParams();
  const { facilityId } = useAuth();
  const requestedPatientId = params.get("patientId") || "";
  const requestedEncounterId = params.get("encounterId") || "";
  const [patients, setPatients] = useState<PatientMap>({});
  const [queues, setQueues] = useState<Queue[]>([]);
  const [entries, setEntries] = useState<QueueEntry[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [catalogue, setCatalogue] = useState<LabTest[]>([]);
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [activeEntry, setActiveEntry] = useState<QueueEntry | null>(null);
  const [order, setOrder] = useState<LabOrderDetail | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [priority, setPriority] = useState<Priority>("NORMAL");
  const [resultInputs, setResultInputs] = useState<Record<string, string>>({});
  const [samples, setSamples] = useState<Record<string, string>>({});
  const [destinationDepartmentId, setDestinationDepartmentId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const labQueueIds = useMemo(() => new Set(queues.filter((q) => { const department = departments.find((d) => d.id === q.department_id); return /laboratory|lab/i.test(`${department?.name || ""} ${department?.code || ""} ${q.name}`); }).map((q) => q.id)), [queues, departments]);
  const labEntries = useMemo(() => entries.filter((entry) => labQueueIds.has(entry.queue_id) && ["WAITING", "CALLED", "IN_SERVICE"].includes(entry.status)), [entries, labQueueIds]);
  const patientName = (id: string) => { const p = patients[id]; return p ? [p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ") : "Patient"; };
  const selectedTests = catalogue.filter((test) => selected.includes(test.id));
  const total = selectedTests.reduce((sum, test) => sum + Number(test.price), 0);
  const allVerified = !!order && order.items.length > 0 && order.items.every((item) => item.status === "RESULT_VERIFIED");

  async function load() {
    if (!facilityId) { setError("FACILITY_CONTEXT_REQUIRED"); setLoading(false); return; }
    setLoading(true); setError("");
    try {
      const [patientResponse, queueResponse, departmentResponse, tests] = await Promise.all([api.listPatients(200, 0), api.listQueues(), api.listDepartments(facilityId), api.listLabTests()]);
      const map: PatientMap = {}; patientResponse.items.forEach((p) => { map[p.id] = p; });
      setPatients(map); setQueues(queueResponse); setDepartments(departmentResponse); setCatalogue(tests);
      const allEntries = await api.listQueueEntries(); setEntries(allEntries);
      if (requestedEncounterId) {
        const nextEncounter = await api.getEncounter(requestedEncounterId); setEncounter(nextEncounter);
        const matching = allEntries.find((e) => e.encounter_id === requestedEncounterId && labQueueIds.has(e.queue_id));
        if (matching) setActiveEntry(matching);
      }
    } catch (e) { setError(e instanceof ApiError ? e.code : "LAB_WORKFLOW_LOAD_FAILED"); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [facilityId, requestedEncounterId]);
  useEffect(() => { if (!departments.length || !encounter) return; const preferred = departments.find((d) => d.id === encounter.department_id && !/laboratory|lab/i.test(`${d.name} ${d.code}`)); if (preferred) setDestinationDepartmentId(preferred.id); }, [departments, encounter]);

  async function receiveIncomingPatient() {
    if (!requestedPatientId || !requestedEncounterId) return;
    try {
      const labDepartment = departments.find((d) => /laboratory|lab/i.test(`${d.name} ${d.code}`));
      if (!labDepartment) throw new Error("LABORATORY_DEPARTMENT_NOT_CONFIGURED");
      const entry = await api.handoffPatient({ patient_id: requestedPatientId, encounter_id: requestedEncounterId, destination_department_id: labDepartment.id, priority, reason: "Laboratory investigation" });
      setActiveEntry(entry); setEncounter(await api.getEncounter(requestedEncounterId)); setMessage(`${patientName(requestedPatientId)} has been sent to the laboratory queue.`); await load();
    } catch (e) { setError(e instanceof ApiError ? e.code : e instanceof Error ? e.message : "LAB_HANDOFF_FAILED"); }
  }
  async function callPatient(entry: QueueEntry) { try { const updated = await api.updateQueueEntryStatus(entry.id, "CALLED"); setEntries((current) => current.map((e) => e.id === updated.id ? updated : e)); setActiveEntry(updated); setMessage(`${patientName(updated.patient_id)} has been called to the laboratory.`); } catch (e) { setError(e instanceof ApiError ? e.code : "LAB_CALL_FAILED"); } }
  async function receivePatient(entry: QueueEntry) { try { const updated = await api.updateQueueEntryStatus(entry.id, "IN_SERVICE"); setEntries((current) => current.map((e) => e.id === updated.id ? updated : e)); setActiveEntry(updated); if (updated.encounter_id) setEncounter(await api.getEncounter(updated.encounter_id)); setMessage(`${patientName(updated.patient_id)} is now received in the laboratory.`); } catch (e) { setError(e instanceof ApiError ? e.code : "LAB_RECEIVE_FAILED"); } }
  async function createOrder() { if (!encounter || !activeEntry || activeEntry.status !== "IN_SERVICE" || selected.length === 0) return; try { const created = await api.createLabOrder({ encounter_id: encounter.id, priority, items: selected.map((test_id) => ({ test_id })) }); setOrder(await api.getLabOrder(created.id)); setMessage("Laboratory order created for the received patient."); } catch (e) { setError(e instanceof ApiError ? e.code : "LAB_ORDER_FAILED"); } }
  async function refreshOrder() { if (order) setOrder(await api.getLabOrder(order.id)); }
  async function collectAndReceive(itemId: string) { if (!order) return; try { const sample = await api.collectLabSample(itemId); setSamples((current) => ({ ...current, [itemId]: sample.id })); await api.receiveLabSample(sample.id); await refreshOrder(); setMessage("Specimen collected and received. Record the result below."); } catch (e) { setError(e instanceof ApiError ? e.code : "SPECIMEN_WORKFLOW_FAILED"); } }
  async function recordResult(itemId: string) { if (!order) return; const sampleId = samples[itemId]; const result = resultInputs[itemId]?.trim(); if (!sampleId || !result) return; try { await api.enterLabResult({ lab_order_item_id: itemId, sample_id: sampleId, result }); await refreshOrder(); setMessage("Result recorded. Verify it before forwarding the patient."); } catch (e) { setError(e instanceof ApiError ? e.code : "RESULT_ENTRY_FAILED"); } }
  async function verifyResult(resultId: string) { try { await api.verifyLabResult(resultId); await refreshOrder(); } catch (e) { setError(e instanceof ApiError ? e.code : "RESULT_VERIFY_FAILED"); } }
  async function forwardPatient() { if (!order || !encounter || !activeEntry || !destinationDepartmentId || !allVerified) return; try { await api.handoffPatient({ patient_id: encounter.patient_id, encounter_id: encounter.id, destination_department_id: destinationDepartmentId, priority, reason: "Laboratory results verified; continue clinical care" }); await api.updateQueueEntryStatus(activeEntry.id, "COMPLETED"); setMessage(`${patientName(encounter.patient_id)} has been forwarded to ${departments.find((d) => d.id === destinationDepartmentId)?.name || "the next department"}.`); setActiveEntry(null); setOrder(null); setSelected([]); setSamples({}); setResultInputs({}); await load(); } catch (e) { setError(e instanceof ApiError ? e.code : "LAB_FORWARD_FAILED"); } }

  if (loading) return <section className="page-stack"><div className="card"><strong>Loading laboratory queue…</strong></div></section>;
  return <section className="page-stack">
    <header className="page-heading"><div><p className="eyebrow">Clinical laboratory information system</p><h1>Laboratory</h1><p className="muted">Patients arrive by handoff. Staff call them, receive them by name, perform selected tests, record verified results and forward the same encounter to the next department.</p></div><span className="status-pill">LIVE WORKFLOW</span></header>
    {error && <div className="error">{error}</div>}{message && <div className="success-box">{message}</div>}
    {requestedPatientId && requestedEncounterId && !activeEntry && <article className="card"><div className="row-between"><div><p className="eyebrow">Incoming patient</p><h2>{patientName(requestedPatientId)}</h2><p className="muted">Afya ID: {patients[requestedPatientId]?.afya_id || "—"} · Encounter: {encounter?.encounter_id || "linked encounter"}</p></div><button onClick={receiveIncomingPatient}>Send to laboratory queue</button></div></article>}
    <article className="card"><div className="row-between"><div><p className="eyebrow">Laboratory queue</p><h2>Patients waiting for laboratory</h2><p className="muted">No UUID entry is required. Patients arrive here through a persistent encounter handoff.</p></div><span className="status-pill">{labEntries.length} waiting</span></div><div className="table-wrap"><table><thead><tr><th>Patient</th><th>Priority</th><th>Status</th><th>Encounter</th><th>Action</th></tr></thead><tbody>{labEntries.map((entry) => <tr key={entry.id}><td><strong>{patientName(entry.patient_id)}</strong><br /><small>{patients[entry.patient_id]?.afya_id || "Afya ID unavailable"}</small></td><td>{entry.priority}</td><td><span className="badge">{entry.status}</span></td><td>{entry.encounter_id ? "Linked" : "Missing"}</td><td>{entry.status === "WAITING" && <button onClick={() => callPatient(entry)}>Call patient</button>}{entry.status === "CALLED" && <button onClick={() => receivePatient(entry)}>Receive patient</button>}{entry.status === "IN_SERVICE" && <button onClick={() => { setActiveEntry(entry); void (entry.encounter_id ? api.getEncounter(entry.encounter_id).then(setEncounter) : Promise.resolve()); }}>Open patient</button>}</td></tr>)}{labEntries.length === 0 && <tr><td colSpan={5}><span className="muted">No patients are currently waiting for laboratory.</span></td></tr>}</tbody></table></div></article>
    {activeEntry && encounter && activeEntry.status === "IN_SERVICE" && <>
      <article className="card"><div className="row-between"><div><p className="eyebrow">Patient received</p><h2>{patientName(encounter.patient_id)}</h2><p className="muted">{patients[encounter.patient_id]?.afya_id || "Afya ID"} · {encounter.encounter_id} · {departments.find((d) => d.id === encounter.department_id)?.name || "Clinical department"}</p></div><span className="status-pill">IN LABORATORY</span></div></article>
      {!order && <article className="card"><div className="row-between"><div><h2>1. Select and perform tests</h2><p className="muted">Tap the examinations required for this patient. The encounter is already linked.</p></div><div className="lab-total-card"><small>Order total</small><strong>KES {total.toLocaleString()}</strong></div></div><div className="lab-add-grid"><label>Priority<select value={priority} onChange={(e) => setPriority(e.target.value as Priority)}><option value="NORMAL">NORMAL</option><option value="URGENT">URGENT</option><option value="EMERGENCY">EMERGENCY</option></select></label></div><div className="lab-test-grid">{catalogue.map((test) => <label key={test.id} className={selected.includes(test.id) ? "lab-test-card selected" : "lab-test-card"}><input type="checkbox" checked={selected.includes(test.id)} onChange={() => setSelected((current) => current.includes(test.id) ? current.filter((id) => id !== test.id) : [...current, test.id])} /><div><div className="row-between"><strong>{test.name}</strong><strong>KES {Number(test.price).toLocaleString()}</strong></div><p className="muted">{test.code} · {test.category || "Laboratory"}</p><p>{test.description || "Laboratory examination"}</p><small>Specimen: {test.sample_type || "Not specified"}</small></div></label>)}</div><div className="form-actions"><button disabled={!selected.length} onClick={createOrder}>Start selected tests</button></div></article>}
      {order && <><article className="card"><div className="row-between"><div><h2>2. Perform tests & record results</h2><p className="muted">Each test remains linked to this patient and encounter. Use one action to collect and receive the specimen, then record and verify the result.</p></div><span className="status-pill">{order.status}</span></div><div className="table-wrap"><table><thead><tr><th>Test</th><th>Specimen</th><th>Result</th><th>Billing</th><th>Action</th></tr></thead><tbody>{order.items.map((item) => <tr key={item.id}><td><strong>{item.test_name}</strong><br /><small>{item.test_code}</small></td><td><span className="badge">{item.status}</span><br /><small>{item.sample_type || "—"}</small></td><td>{item.result ? <><strong>{item.result.result}</strong>{item.result.unit && ` ${item.result.unit}`}<br /><small>{item.result.status}</small></> : <input value={resultInputs[item.id] || ""} placeholder="Enter laboratory result" disabled={!samples[item.id] || item.status !== "SAMPLE_RECEIVED"} onChange={(e) => setResultInputs((current) => ({ ...current, [item.id]: e.target.value }))} />}</td><td><strong>KES {Number(item.price).toLocaleString()}</strong>{item.charge_id && <><br /><small>Charged</small></>}</td><td>{item.status === "ORDERED" && <button onClick={() => collectAndReceive(item.id)}>Collect & receive</button>}{item.status === "SAMPLE_RECEIVED" && <button disabled={!resultInputs[item.id]?.trim()} onClick={() => recordResult(item.id)}>Record result</button>}{item.status === "RESULT_ENTERED" && item.result && <button onClick={() => verifyResult(item.result!.id)}>Verify result</button>}{item.status === "RESULT_VERIFIED" && <span className="status-pill">VERIFIED</span>}</td></tr>)}</tbody></table></div></article>
        <article className="card"><h2>3. Forward patient to the next department</h2><p className="muted">Verified laboratory work is complete. Choose the next destination; the same patient and encounter will be placed in that department's queue.</p><div className="lab-add-grid"><label>Next department<select value={destinationDepartmentId} onChange={(e) => setDestinationDepartmentId(e.target.value)}><option value="">Select next step</option>{departments.filter((d) => d.id !== encounter.department_id && !/laboratory|lab/i.test(`${d.name} ${d.code}`)).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label></div><div className="form-actions"><button disabled={!allVerified || !destinationDepartmentId} onClick={forwardPatient}>{allVerified ? "Forward patient" : "Complete and verify all results first"}</button></div></article></>}
    </>}
    <style>{`@media(max-width:800px){.page-heading{display:block}.page-heading .status-pill{display:inline-block;margin-top:12px}.table-wrap{overflow-x:auto}.lab-add-grid{grid-template-columns:1fr!important}.lab-test-grid{grid-template-columns:1fr!important}.row-between{gap:12px;align-items:flex-start}button{max-width:100%}}`}</style>
  </section>;
}
