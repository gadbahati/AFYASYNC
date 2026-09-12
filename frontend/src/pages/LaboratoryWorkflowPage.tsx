import { useMemo, useState } from "react";
import "./lab.css";

type LabTest = { id: string; code: string; name: string; category: string; description: string; specimen: string; price: number };
type LabRecord = LabTest & { result: string; status: "PENDING" | "PERFORMED" | "RESULTED" };

const DEMO_TESTS: LabTest[] = [
  { id: "fbc", code: "FBC", name: "Full Blood Count", category: "Haematology", description: "Measures haemoglobin, white cells, platelets and related blood indices.", specimen: "EDTA whole blood", price: 650 },
  { id: "malaria", code: "MAL-RDT", name: "Malaria Rapid Diagnostic Test", category: "Parasitology", description: "Screens for malaria infection using a rapid diagnostic blood test.", specimen: "Whole blood", price: 350 },
  { id: "rbs", code: "RBS", name: "Random Blood Sugar", category: "Chemistry", description: "Measures blood glucose at the time the specimen is collected.", specimen: "Fluoride plasma / capillary blood", price: 250 },
  { id: "urinalysis", code: "UA", name: "Urinalysis", category: "Clinical microscopy", description: "Examines urine for physical, chemical and microscopic findings.", specimen: "Midstream urine", price: 450 },
  { id: "lft", code: "LFT", name: "Liver Function Tests", category: "Clinical chemistry", description: "Panel assessing liver-related enzymes, proteins and bilirubin.", specimen: "Serum", price: 1500 },
  { id: "ufb", code: "U&E", name: "Urea & Electrolytes", category: "Clinical chemistry", description: "Assesses urea and key electrolytes used in renal and fluid assessment.", specimen: "Serum / plasma", price: 1200 },
];

export function LaboratoryWorkflowPage() {
  const [selected, setSelected] = useState<string[]>(["fbc", "malaria"]);
  const [records, setRecords] = useState<Record<string, LabRecord>>({
    fbc: { ...DEMO_TESTS[0], result: "Hb 12.8 g/dL · WBC 7.2 ×10⁹/L · Platelets 286 ×10⁹/L", status: "RESULTED" },
    malaria: { ...DEMO_TESTS[1], result: "Negative", status: "RESULTED" },
  });
  const [showAdd, setShowAdd] = useState(false);
  const [customTests, setCustomTests] = useState<LabTest[]>([]);
  const [newTest, setNewTest] = useState({ name: "", code: "", description: "", specimen: "", price: "" });
  const [forwarded, setForwarded] = useState(false);
  const [message, setMessage] = useState("Select tests, record each result, then forward the completed laboratory findings to prescription review.");

  const allTests = useMemo(() => [...DEMO_TESTS, ...customTests], [customTests]);
  const selectedTests = allTests.filter((test) => selected.includes(test.id));
  const total = selectedTests.reduce((sum, test) => sum + test.price, 0);
  const completed = selectedTests.filter((test) => records[test.id]?.status === "RESULTED" && records[test.id]?.result.trim()).length;

  function toggle(id: string) {
    setSelected((current) => current.includes(id) ? current.filter((x) => x !== id) : [...current, id]);
    setForwarded(false);
  }

  function recordResult(test: LabTest, result: string) {
    setRecords((current) => ({ ...current, [test.id]: { ...test, result, status: result.trim() ? "RESULTED" : "PENDING" } }));
    setForwarded(false);
  }

  function markPerformed(test: LabTest) {
    setRecords((current) => ({ ...current, [test.id]: { ...(current[test.id] ?? test), result: current[test.id]?.result ?? "", status: "PERFORMED" } }));
    setMessage(`${test.name} marked as performed. Enter the result before forwarding.`);
  }

  function addTest() {
    const price = Number(newTest.price);
    if (!newTest.name.trim() || !newTest.code.trim() || !newTest.description.trim() || !newTest.specimen.trim() || !Number.isFinite(price) || price <= 0) return;
    const test: LabTest = { id: `custom-${Date.now()}`, code: newTest.code.trim().toUpperCase(), name: newTest.name.trim(), category: "Custom laboratory", description: newTest.description.trim(), specimen: newTest.specimen.trim(), price };
    setCustomTests((current) => [...current, test]);
    setSelected((current) => [...current, test.id]);
    setNewTest({ name: "", code: "", description: "", specimen: "", price: "" });
    setShowAdd(false);
    setMessage(`${test.name} added to this laboratory order at KES ${price.toLocaleString()}.`);
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Clinical laboratory information system</p>
          <h1>Laboratory</h1>
          <p className="muted">Order tests, track each examination, capture individual results, calculate test-level charges and forward completed findings to the clinician.</p>
        </div>
        <div className="form-actions"><span className="status-pill">DEMO WORKFLOW</span><button onClick={() => setShowAdd((value) => !value)}>{showAdd ? "Close add test" : "+ Add test"}</button></div>
      </header>

      <div className="success-box"><strong>Laboratory demo is active.</strong> This is the laboratory stage that connects testing → results → prescription review → pharmacy.</div>

      <article className="card">
        <div className="row-between"><div><h2>Laboratory workflow</h2><p className="muted">A real-world style sequence for an encounter. Each test is handled as its own clinical and billing item.</p></div><span className="badge">{completed}/{selectedTests.length} RESULTS READY</span></div>
        <div className="lab-workflow-strip">
          {["Order test", "Collect specimen", "Perform test", "Record result", "Bill test", "Forward to clinician"].map((step, index) => <div className="lab-workflow-step" key={step}><span>{index + 1}</span><strong>{step}</strong></div>)}
        </div>
      </article>

      {showAdd && <article className="card">
        <div className="row-between"><div><h2>+ Add laboratory test</h2><p className="muted">Every new test gets its own code, description, specimen requirement and standalone price.</p></div><span className="badge">TEST CATALOGUE</span></div>
        <div className="lab-add-grid">
          <label>Test name<input value={newTest.name} placeholder="e.g. Kidney Function Test" onChange={(e) => setNewTest({ ...newTest, name: e.target.value })} /></label>
          <label>Test code<input value={newTest.code} placeholder="e.g. KFT" onChange={(e) => setNewTest({ ...newTest, code: e.target.value })} /></label>
          <label>Specimen / sample<input value={newTest.specimen} placeholder="e.g. Serum" onChange={(e) => setNewTest({ ...newTest, specimen: e.target.value })} /></label>
          <label>Price (KES)<input type="number" min="1" value={newTest.price} placeholder="e.g. 1200" onChange={(e) => setNewTest({ ...newTest, price: e.target.value })} /></label>
          <label className="lab-add-wide">Description<textarea value={newTest.description} placeholder="What this examination measures or helps assess" onChange={(e) => setNewTest({ ...newTest, description: e.target.value })} /></label>
        </div>
        <div className="form-actions"><button disabled={!newTest.name.trim() || !newTest.code.trim() || !newTest.description.trim() || !newTest.specimen.trim() || Number(newTest.price) <= 0} onClick={addTest}>Add test to order</button><button className="button secondary" onClick={() => setShowAdd(false)}>Cancel</button></div>
      </article>}

      <article className="card">
        <div className="row-between"><div><h2>1. Add / select tests</h2><p className="muted">Choose the examinations requested by the clinician. Each test has its own description, specimen and price.</p></div><div className="lab-total-card"><small>Current laboratory total</small><strong>KES {total.toLocaleString()}</strong></div></div>
        <div className="lab-test-grid">{allTests.map((test) => <label key={test.id} className={selected.includes(test.id) ? "lab-test-card selected" : "lab-test-card"}><input type="checkbox" checked={selected.includes(test.id)} onChange={() => toggle(test.id)} /><div><div className="row-between"><strong>{test.name}</strong><strong>KES {test.price.toLocaleString()}</strong></div><p className="muted">{test.code} · {test.category}</p><p>{test.description}</p><small>Specimen: {test.specimen}</small></div></label>)}</div>
      </article>

      <article className="card">
        <div className="row-between"><div><h2>2. Individual test records</h2><p className="muted">Every examination is written down separately. Enter the observation/result and its workflow status.</p></div><span className="status-pill">{completed} OF {selectedTests.length} COMPLETE</span></div>
        <div className="table-wrap"><table><thead><tr><th>Test</th><th>Description</th><th>Specimen</th><th>Price</th><th>Result / observation</th><th>Status</th></tr></thead><tbody>{selectedTests.map((test) => { const record = records[test.id]; return <tr key={test.id}><td><strong>{test.name}</strong><br /><small>{test.code}</small></td><td>{test.description}</td><td>{test.specimen}</td><td><strong>KES {test.price.toLocaleString()}</strong></td><td><input value={record?.result ?? ""} placeholder="Enter laboratory result" onChange={(e) => recordResult(test, e.target.value)} /></td><td>{record?.status === "RESULTED" ? <span className="status-pill">RESULTED</span> : record?.status === "PERFORMED" ? <span className="badge">PERFORMED</span> : <button className="button secondary" onClick={() => markPerformed(test)}>Mark performed</button>}</td></tr>; })}</tbody></table></div>
      </article>

      <article className="card">
        <div className="row-between"><div><h2>3. Test-by-test billing</h2><p className="muted">Laboratory charges are separate line items. The total is calculated from the individual test prices.</p></div><strong>KES {total.toLocaleString()}</strong></div>
        <div className="lab-summary">{selectedTests.map((test) => <div className="billing-line" key={test.id}><div><strong>{test.name}</strong><p className="muted">{test.code} · {records[test.id]?.status === "RESULTED" ? "Resulted" : "Pending"}</p></div><span>1 ×</span><strong>KES {test.price.toLocaleString()}</strong></div>)}</div>
        <div className="billing-total">Laboratory total: KES {total.toLocaleString()}</div>
      </article>

      <article className="card">
        <div className="row-between"><div><h2>4. Forward completed results to prescription review</h2><p className="muted">Results go to the authorized clinician for interpretation and prescription decisions. The laboratory does not automatically prescribe medicine.</p></div><span className={completed === selectedTests.length && selectedTests.length > 0 ? "status-pill" : "badge"}>{completed === selectedTests.length && selectedTests.length > 0 ? "READY TO FORWARD" : "WAITING"}</span></div>
        <div className="lab-summary">{selectedTests.map((test) => <div className="billing-line" key={test.id}><div><strong>{test.name}</strong><p className="muted">{records[test.id]?.result || "Result pending"}</p></div><span className={records[test.id]?.status === "RESULTED" ? "status-pill" : "badge"}>{records[test.id]?.status === "RESULTED" ? "READY" : "PENDING"}</span></div>)}</div>
        <div className="form-actions"><button disabled={selectedTests.length === 0 || completed !== selectedTests.length} onClick={() => { setForwarded(true); setMessage("All laboratory tests are recorded. Results have been forwarded to prescription review."); }}>{forwarded ? "✓ Results forwarded" : "Forward results to prescription review"}</button></div>
        {forwarded && <div className="success-box"><strong>LABORATORY COMPLETE</strong> · Individual results recorded · Test charges KES {total.toLocaleString()} · Results forwarded to clinician · Prescription review is now available.</div>}
      </article>

      <div className="info-box"><strong>Demo hand-off:</strong> after forwarding, continue to <strong>Prescription</strong> → <strong>Pharmacy stock</strong> → <strong>Dispensing</strong> → <strong>Billing</strong> → <strong>SHA claim</strong>.</div>
      <div className="muted small">{message}</div>
    </section>
  );
}
