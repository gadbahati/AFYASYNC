import { useMemo, useState } from "react";

const MEMBERS = [
  { number: "SHA-0019283746", name: "Amina Wanjiku", dob: "12 Apr 1992", sex: "Female", status: "ACTIVE", package: "SHA-08 · MCH + Child Health", care: "INPATIENT", coverage: "VERIFIED" },
  { number: "SHA-0048172930", name: "Brian Otieno Ochieng", dob: "03 Nov 1985", sex: "Male", status: "ACTIVE", package: "SHA-07 · Inpatient", care: "INPATIENT", coverage: "VERIFIED" },
];
const MEDICINES = [
  { id: "amox", name: "Amoxicillin 500 mg", stock: 84, unit: "capsules", price: 18 },
  { id: "para", name: "Paracetamol 500 mg", stock: 240, unit: "tablets", price: 5 },
  { id: "iron", name: "Ferrous Sulphate 200 mg", stock: 120, unit: "tablets", price: 12 },
  { id: "folate", name: "Folic Acid 5 mg", stock: 96, unit: "tablets", price: 8 },
  { id: "cef", name: "Ceftriaxone 1 g", stock: 30, unit: "vials", price: 420 },
];
const STEPS = ["SHA verification", "Pre-authorisation", "Care episode", "Vitals / doctor", "MCH / inpatient services", "Prescription", "Pharmacy stock", "Dispensing", "Charges", "SHA claim", "Submission", "Reconciliation"];
type Line = { medicineId: string; frequency: string; duration: string; quantity: number };

export function ShaCareDemoPage() {
  const [query, setQuery] = useState("SHA-0019283746");
  const [member, setMember] = useState<(typeof MEMBERS)[number] | null>(null);
  const [careSetting, setCareSetting] = useState<"INPATIENT" | "OUTPATIENT">("INPATIENT");
  const [preauth, setPreauth] = useState(false);
  const [preauthStatus, setPreauthStatus] = useState("PENDING");
  const [admitted, setAdmitted] = useState(false);
  const [ward, setWard] = useState("Maternity Ward");
  const [bed, setBed] = useState("M-08");
  const [diagnosis, setDiagnosis] = useState("Antenatal observation / delivery care");
  const [vitals, setVitals] = useState(false);
  const [doctor, setDoctor] = useState(false);
  const [services, setServices] = useState<string[]>([]);
  const [selectedMedicine, setSelectedMedicine] = useState(MEDICINES[0].id);
  const [quantity, setQuantity] = useState(10);
  const [prescription, setPrescription] = useState<Line[]>([]);
  const [dispensed, setDispensed] = useState(false);
  const [claim, setClaim] = useState("DRAFT");
  const [reconciled, setReconciled] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const selected = useMemo(() => MEDICINES.find((m) => m.id === selectedMedicine)!, [selectedMedicine]);
  const chargeTotal = services.length * 850 + prescription.reduce((sum, line) => sum + (MEDICINES.find((m) => m.id === line.medicineId)?.price ?? 0) * line.quantity, 0);
  const completed = [!!member, preauthStatus === "AUTHORIZED", admitted, vitals && doctor, services.length > 0, prescription.length > 0, prescription.length > 0, dispensed, chargeTotal > 0, claim !== "DRAFT", claim === "SUBMITTED", reconciled];
  const progress = Math.round((completed.filter(Boolean).length / STEPS.length) * 100);
  function verify() { const found = MEMBERS.find((m) => m.number.toLowerCase() === query.trim().toLowerCase()); setMember(found ?? null); setPreauth(false); setPreauthStatus("PENDING"); setAdmitted(false); setClaim("DRAFT"); setReconciled(false); setMessage(found ? `${found.name} verified. Coverage is ${found.coverage}.` : "Member not found. Try SHA-0019283746."); }
  function requestAuthorization() { if (!member) return; setPreauth(true); setPreauthStatus("PENDING"); setMessage("Pre-authorisation request created and queued for decision."); }
  function approveAuthorization() { setPreauthStatus("AUTHORIZED"); setMessage("Pre-authorisation AUTHORIZED. Care can proceed."); }
  function startCare() { if (preauthStatus !== "AUTHORIZED") return; setAdmitted(true); setMessage(`${member?.name} started ${careSetting.toLowerCase()} care.`); }
  function addService(name: string) { setServices((current) => current.includes(name) ? current.filter((x) => x !== name) : [...current, name]); }
  function addPrescription() { if (quantity < 1 || quantity > selected.stock) { setMessage(`Quantity must be between 1 and ${selected.stock}.`); return; } setPrescription((current) => [...current, { medicineId: selected.id, frequency: "TDS", duration: "5 days", quantity }]); setMessage(`${selected.name} added to the prescription.`); }
  function submitClaim() { if (!chargeTotal) return; setClaim("READY"); setMessage("Charges compiled into a SHA claim draft and validated."); }
  function sendClaim() { if (claim !== "READY") return; setClaim("SUBMITTED"); setMessage("Claim submitted to the payer integration queue."); }
  function reconcile() { if (claim !== "SUBMITTED") return; setReconciled(true); setMessage("Payer response recorded and reconciliation completed with no variance."); }
  return <section className="page-stack">
    <div className="page-heading"><div><p className="eyebrow">Stakeholder demonstration</p><h1>SHA end-to-end care workflow</h1><p className="muted">Verification → pre-authorisation → care → pharmacy → charges → claim → reconciliation.</p></div><span className="badge">DEMO ONLY · {progress}%</span></div>
    <article className="card"><h2>Workflow status</h2><div className="table-wrap"><table><thead><tr>{STEPS.map((step, i) => <th key={step}>{i + 1}. {step}</th>)}</tr></thead><tbody><tr>{completed.map((done, i) => <td key={i}><span className={done ? "status-pill" : "badge"}>{done ? "DONE" : "PENDING"}</span></td>)}</tr></tbody></table></div></article>
    <article className="card"><h2>1. SHA verification</h2><p className="muted">Search the member / identification number and load identity and active benefit coverage.</p><div className="form-grid"><label>SHA member / ID number<input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && verify()} /></label><div className="form-actions"><button onClick={verify}>Verify SHA</button></div></div>{member && <div className="patient-verification"><div><span className="muted small">Member</span><strong>{member.number}</strong></div><div><span className="muted small">Patient</span><strong>{member.name}</strong></div><div><span className="muted small">DOB / Sex</span><strong>{member.dob} · {member.sex}</strong></div><div><span className="muted small">Coverage</span><strong>{member.coverage} · {member.package}</strong></div><span className="status-pill">{member.status}</span></div>}</article>
    {member && <article className="card"><h2>2. Pre-authorisation</h2><p className="muted">Request authorisation before the care episode. The production adapter will map this state machine to the approved SHA integration.</p><div className="form-grid"><label>Care setting<select value={careSetting} onChange={(e) => setCareSetting(e.target.value as "INPATIENT" | "OUTPATIENT")}><option value="INPATIENT">Inpatient</option><option value="OUTPATIENT">Outpatient</option></select></label><label>Benefit<input value={member.package} readOnly /></label></div>{!preauth ? <button onClick={requestAuthorization}>Request pre-authorisation</button> : <div className="info-box">Authorization status: <strong>{preauthStatus}</strong>{preauthStatus === "PENDING" && <button className="button secondary" onClick={approveAuthorization}>Approve in demo</button>}</div>}</article>}
    {member && preauthStatus === "AUTHORIZED" && <article className="card"><h2>3–4. Care episode · vitals · doctor</h2><p className="muted">Create the encounter/admission, record observations, then document the clinician assessment.</p><div className="form-grid"><label>Ward<select value={ward} onChange={(e) => setWard(e.target.value)}><option>General Ward</option><option>Maternity Ward</option><option>Paediatric Ward</option><option>Private Ward</option></select></label><label>Bed<input value={bed} onChange={(e) => setBed(e.target.value)} /></label><label className="span-2">Diagnosis / reason<input value={diagnosis} onChange={(e) => setDiagnosis(e.target.value)} /></label></div>{!admitted ? <button onClick={startCare}>{careSetting === "INPATIENT" ? "Start admission" : "Start outpatient encounter"}</button> : <div className="success-box">{careSetting} episode active · {ward} · {bed}</div>}{admitted && <div className="form-actions"><button className="button secondary" onClick={() => setVitals(true)}>Record vitals</button><button className="button secondary" onClick={() => setDoctor(true)}>Complete doctor review</button></div>}{vitals && <div className="info-box">Vitals recorded: BP 118/76 · Pulse 82 · Temp 36.7°C · SpO₂ 98%.</div>}{doctor && <div className="info-box">Doctor review completed: assessment and treatment plan added to the clinical record.</div>}</article>}
    {admitted && vitals && doctor && <article className="card"><h2>5. MCH / inpatient services</h2><p className="muted">Select services that become billable clinical events for the encounter.</p><div className="form-actions">{(careSetting === "INPATIENT" ? ["Ward accommodation", "Nursing care", "Diagnostic tests", "Pharmaceuticals"] : ["Consultation", "Diagnostic tests", "Outpatient medicine"]).map((name) => <button key={name} className={services.includes(name) ? "button" : "button secondary"} onClick={() => addService(name)}>{services.includes(name) ? "✓ " : "+ "}{name}</button>)}</div></article>}
    {services.length > 0 && <article className="card"><h2>6–8. Prescription → pharmacy stock → dispensing</h2><p className="muted">Prescribe from facility stock, send to pharmacy, and complete dispensing with stock control.</p><div className="form-grid"><label>Medicine<select value={selectedMedicine} onChange={(e) => setSelectedMedicine(e.target.value)}>{MEDICINES.map((m) => <option key={m.id} value={m.id}>{m.name} · {m.stock} {m.unit} · KES {m.price}</option>)}</select></label><label>Quantity<input type="number" min="1" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} /></label><div className="form-actions"><button onClick={addPrescription}>Add prescription line</button></div></div>{prescription.length > 0 && <div className="table-wrap"><table><thead><tr><th>Medicine</th><th>Frequency</th><th>Duration</th><th>Qty</th><th>Stock after</th></tr></thead><tbody>{prescription.map((line, i) => { const m = MEDICINES.find((x) => x.id === line.medicineId)!; return <tr key={i}><td>{m.name}</td><td>{line.frequency}</td><td>{line.duration}</td><td>{line.quantity}</td><td>{m.stock - line.quantity}</td></tr>; })}</tbody></table></div>}{prescription.length > 0 && <div className="form-actions"><button className="button secondary" onClick={() => { setDispensed(true); setMessage("Pharmacist verified the prescription and recorded dispensing."); }}>Send to Pharmacy & Dispense</button>{dispensed && <span className="status-pill">DISPENSED</span>}</div>}</article>}
    {prescription.length > 0 && dispensed && <article className="card"><h2>9. Charges → 10–12. SHA claim → submission → reconciliation</h2><p className="muted">Billing/claims compiles encounter charges, validates the claim, queues payer submission, records the response and reconciles payment.</p><div className="patient-verification"><div><span className="muted small">Encounter charges</span><strong>KES {chargeTotal.toLocaleString()}</strong></div><div><span className="muted small">Claim status</span><strong>{claim}</strong></div><div><span className="muted small">Payer</span><strong>SHA</strong></div><div><span className="muted small">Reconciliation</span><strong>{reconciled ? "NO VARIANCE" : "PENDING"}</strong></div></div><div className="form-actions">{claim === "DRAFT" && <button onClick={submitClaim}>Create & validate SHA claim</button>}{claim === "READY" && <button onClick={sendClaim}>Submit claim</button>}{claim === "SUBMITTED" && !reconciled && <button onClick={reconcile}>Record payment & reconcile</button>}{reconciled && <span className="success-box">CLAIM PAID · RECONCILED · KES {chargeTotal.toLocaleString()}</span>}</div></article>}
    {message && <div className="card info-box">{message}</div>}
    <article className="card warning-box"><strong>Demo boundary</strong><p>This stakeholder walkthrough uses seeded members and controlled demo events. The backend now includes a persistent SHA pre-authorisation state machine, while admission, clinical, pharmacy, billing and claims remain the production integration points. The demo does not contact live SHA or dispense real medicine.</p></article>
  </section>;
}
