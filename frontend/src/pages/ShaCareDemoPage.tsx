import { useMemo, useState } from "react";

const MEMBERS = [
  { number: "SHA-0019283746", name: "Amina Wanjiku", dob: "12 Apr 1992", sex: "Female", package: "SHA-08 · MCH + Child Health", coverage: "VERIFIED" },
  { number: "SHA-0048172930", name: "Brian Otieno Ochieng", dob: "03 Nov 1985", sex: "Male", package: "SHA-07 · Inpatient", coverage: "VERIFIED" },
];
const MEDICINES = [
  { id: "para", name: "Paracetamol 500 mg", stock: 240, unit: "tablets", defaultPrice: 5 },
  { id: "amox", name: "Amoxicillin 500 mg", stock: 84, unit: "capsules", defaultPrice: 18 },
  { id: "iron", name: "Ferrous Sulphate 200 mg", stock: 120, unit: "tablets", defaultPrice: 12 },
  { id: "folate", name: "Folic Acid 5 mg", stock: 96, unit: "tablets", defaultPrice: 8 },
  { id: "cef", name: "Ceftriaxone 1 g", stock: 30, unit: "vials", defaultPrice: 420 },
];
const STEPS = ["SHA verification", "Pre-authorisation", "Care episode", "Vitals / doctor", "MCH / inpatient services", "Prescription", "Pharmacy stock", "Dispensing", "Charges", "SHA claim", "Submission", "Reconciliation"];
type BillingLine = { id: string; description: string; quantity: number; price: number };
type Referral = { id: string; patient: string; destination: string; reason: string; status: "SENT" | "ACCEPTED" | "DECLINED" };

export function ShaCareDemoPage() {
  const [query, setQuery] = useState("SHA-0019283746");
  const [member, setMember] = useState<(typeof MEMBERS)[number] | null>(null);
  const [preauth, setPreauth] = useState("PENDING");
  const [admitted, setAdmitted] = useState(false);
  const [released, setReleased] = useState(false);
  const [vitals, setVitals] = useState(false);
  const [doctor, setDoctor] = useState(false);
  const [services, setServices] = useState<string[]>([]);
  const [selectedMedicine, setSelectedMedicine] = useState("para");
  const [quantity, setQuantity] = useState(20);
  const [dispensed, setDispensed] = useState(false);
  const [claim, setClaim] = useState("PENDING");
  const [reconciled, setReconciled] = useState(false);
  const [referral, setReferral] = useState<Referral | null>(null);
  const [appointmentBooked, setAppointmentBooked] = useState(false);
  const [appointmentDate, setAppointmentDate] = useState("2026-09-20T10:00");
  const [destination, setDestination] = useState("County Referral Hospital");
  const [message, setMessage] = useState<string | null>(null);
  const [billing, setBilling] = useState<BillingLine[]>([
    { id: "consult", description: "Doctor consultation", quantity: 1, price: 850 },
  ]);
  const selected = useMemo(() => MEDICINES.find((m) => m.id === selectedMedicine)!, [selectedMedicine]);
  const total = billing.reduce((sum, line) => sum + line.quantity * line.price, 0);
  const completed = [!!member, preauth === "AUTHORIZED", admitted, vitals && doctor, services.length > 0, billing.some((x) => x.description.toLowerCase().includes("medicine")), billing.some((x) => x.description.toLowerCase().includes("medicine")), dispensed, total > 0, claim !== "PENDING", claim === "SUBMITTED", reconciled];
  const progress = Math.round((completed.filter(Boolean).length / STEPS.length) * 100);

  function verify() {
    const found = MEMBERS.find((m) => m.number.toLowerCase() === query.trim().toLowerCase());
    setMember(found ?? null); setPreauth("PENDING"); setAdmitted(false); setReleased(false); setDispensed(false); setClaim("PENDING"); setReconciled(false); setReferral(null); setAppointmentBooked(false);
    setMessage(found ? `${found.name} verified. Active ${found.package} coverage found.` : "Member not found. Try SHA-0019283746.");
  }
  function addService(name: string) { setServices((current) => current.includes(name) ? current.filter((x) => x !== name) : [...current, name]); }
  function addMedicineCharge() {
    if (quantity < 1 || quantity > selected.stock) { setMessage(`Quantity must be between 1 and ${selected.stock}.`); return; }
    setBilling((current) => [...current, { id: crypto.randomUUID(), description: `${selected.name} (dispensed)`, quantity, price: selected.defaultPrice }]);
    setMessage(`${selected.name} added. The pharmacy price is independently editable.`);
  }
  function sendReferral() {
    if (!member) return;
    setReferral({ id: `REF-DEMO-${Date.now().toString().slice(-5)}`, patient: member.name, destination, reason: "Requires specialist / higher-level care", status: "SENT" });
    setMessage(`Referral sent to ${destination}. The receiving facility can accept or decline it.`);
  }
  function decideReferral(status: "ACCEPTED" | "DECLINED") {
    setReferral((current) => current ? { ...current, status } : current);
    setMessage(status === "ACCEPTED" ? "Receiving hospital accepted the referred patient." : "Receiving hospital declined the referral and the source facility was notified.");
  }
  function releasePatient() {
    setReleased(true); setAdmitted(false); setMessage(`${member?.name ?? "Patient"} has been released after pharmacy dispensing. The encounter is marked ready for discharge/closure.`);
  }
  function updatePrice(id: string, value: number) { setBilling((current) => current.map((line) => line.id === id ? { ...line, price: Number.isFinite(value) ? value : 0 } : line)); }

  return <section className="page-stack">
    <style>{`.demo-flow{display:grid;gap:10px}.demo-step{display:grid;grid-template-columns:38px 1fr auto;gap:12px;align-items:center;padding:12px 14px;border:1px solid var(--border);border-radius:10px;background:var(--surface)}.demo-step.done{background:var(--brand-tint);border-color:var(--brand-tint-strong)}.demo-number{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;background:var(--canvas);font-family:var(--font-mono);font-size:12px;font-weight:600}.demo-step.done .demo-number{background:var(--brand);color:#fff}.demo-title{font-weight:600}.demo-actions{display:flex;gap:8px;flex-wrap:wrap}.billing-line{display:grid;grid-template-columns:1fr 90px 130px 120px;gap:10px;align-items:end;padding:10px 0;border-bottom:1px solid var(--border)}.billing-total{display:flex;justify-content:flex-end;font-size:20px;font-weight:700;color:var(--brand-dark);padding-top:14px}@media(max-width:760px){.billing-line{grid-template-columns:1fr 1fr}.demo-step{grid-template-columns:34px 1fr}.demo-step>.status-pill{grid-column:2}}`}</style>
    <div className="page-heading"><div><p className="eyebrow">Stakeholder demonstration</p><h1>SHA & AfyaSync care workflow</h1><p className="muted">A complete visual walkthrough including referrals, follow-ups, appointments, pharmacy release and itemised billing.</p></div><span className="badge">DEMO ONLY · {progress}%</span></div>

    <article className="card"><h2>Workflow status</h2><p className="muted">Vertical clinical and financial journey. Each stage changes as the demo is completed.</p><div className="demo-flow">{STEPS.map((step, i) => <div key={step} className={`demo-step ${completed[i] ? "done" : ""}`}><span className="demo-number">{i + 1}</span><div><div className="demo-title">{step}</div><span className="muted small">{completed[i] ? "Completed" : "Waiting for the previous step"}</span></div><span className={completed[i] ? "status-pill" : "badge"}>{completed[i] ? "DONE" : "PENDING"}</span></div>)}</div></article>

    <article className="card"><h2>1. SHA verification</h2><p className="muted">Verify the patient before using the SHA pathway.</p><div className="form-grid"><label>SHA membership number<input value={query} onChange={(e) => setQuery(e.target.value)} /></label><div className="form-actions"><button onClick={verify}>Verify patient</button></div></div>{member && <div className="patient-verification"><div><span className="muted small">Patient</span><strong>{member.name}</strong></div><div><span className="muted small">DOB / Sex</span><strong>{member.dob} · {member.sex}</strong></div><div><span className="muted small">Coverage</span><strong>{member.coverage} · {member.package}</strong></div><span className="status-pill">VERIFIED</span></div>}</article>

    {member && <article className="card"><h2>2. Pre-authorisation</h2><p className="muted">Care cannot start until authorisation is approved.</p>{preauth === "PENDING" ? <div className="demo-actions"><button onClick={() => { setMessage("Pre-authorisation request created."); }}>Request pre-authorisation</button><button className="button secondary" onClick={() => { setPreauth("AUTHORIZED"); setMessage("Demo payer authorised the requested care."); }}>Approve in demo</button></div> : <div className="success-box">PRE-AUTHORISED · Care may proceed</div>}</article>}

    {member && preauth === "AUTHORIZED" && <article className="card"><h2>3–4. Care episode · vitals · doctor</h2><div className="form-grid"><label>Ward / department<select><option>General Ward</option><option>Maternity Ward</option><option>Paediatric Ward</option></select></label><label>Bed<input defaultValue="M-08" /></label><label className="span-2">Diagnosis / reason<input defaultValue="Clinical observation and treatment" /></label></div><div className="demo-actions">{!admitted && !released && <button onClick={() => { setAdmitted(true); setMessage("Care episode started and patient admitted."); }}>Admit patient</button>}{admitted && <><button className="button secondary" onClick={() => setVitals(true)}>Record vitals</button><button className="button secondary" onClick={() => setDoctor(true)}>Complete doctor review</button></>}{released && <span className="status-pill">RELEASED</span>}</div>{vitals && <div className="info-box">Vitals recorded · BP 118/76 · Pulse 82 · Temp 36.7°C · SpO₂ 98%.</div>}{doctor && <div className="info-box">Doctor consultation completed · assessment and treatment plan documented.</div>}</article>}

    {admitted && vitals && doctor && <article className="card"><h2>5. MCH / inpatient services</h2><p className="muted">Select services performed during the encounter.</p><div className="demo-actions">{["Ward accommodation", "Nursing care", "Diagnostic tests", "MCH service"].map((name) => <button key={name} className={services.includes(name) ? "button" : "button secondary"} onClick={() => addService(name)}>{services.includes(name) ? "✓ " : "+ "}{name}</button>)}</div></article>}

    {(admitted || released) && <article className="card"><h2>6–8. Prescription · pharmacy stock · dispensing</h2><p className="muted">The medicine is selected from stock, priced independently, dispensed and then the patient can be released.</p><div className="form-grid"><label>Medicine<select value={selectedMedicine} onChange={(e) => setSelectedMedicine(e.target.value)}>{MEDICINES.map((m) => <option key={m.id} value={m.id}>{m.name} · {m.stock} {m.unit}</option>)}</select></label><label>Quantity<input type="number" min="1" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} /></label></div><div className="demo-actions"><button onClick={addMedicineCharge}>Add to prescription & billing</button>{billing.some((x) => x.description.includes("dispensed")) && !dispensed && <button className="button secondary" onClick={() => { setDispensed(true); setMessage("Pharmacy received the prescription, deducted stock and recorded dispensing."); }}>Pharmacy: dispense medicine</button>}{dispensed && !released && <button className="button secondary" onClick={releasePatient}>Release patient</button>}{released && <span className="status-pill">PATIENT RELEASED</span>}</div>{dispensed && <div className="success-box">PHARMACY DISPENSED · Stock updated · Patient released when discharge action is completed.</div>}</article>}

    {member && <article className="card"><h2>Referral / transfer to another hospital</h2><p className="muted">A patient who is admitted or receiving care can be referred. The receiving hospital has its own accept/decline decision.</p><div className="form-grid"><label>Receiving facility<select value={destination} onChange={(e) => setDestination(e.target.value)}><option>County Referral Hospital</option><option>Kerugoya Referral Hospital</option><option>Regional Teaching Hospital</option></select></label><label>Reason<input defaultValue="Requires specialist / higher-level care" /></label></div><div className="demo-actions"><button onClick={sendReferral}>Refer patient</button>{referral?.status === "SENT" && <><button className="button secondary" onClick={() => decideReferral("ACCEPTED")}>Receiving hospital: Accept</button><button className="button secondary" onClick={() => decideReferral("DECLINED")}>Receiving hospital: Decline</button></>}</div>{referral && <div className="patient-verification"><div><span className="muted small">Referral</span><strong>{referral.id}</strong></div><div><span className="muted small">Destination</span><strong>{referral.destination}</strong></div><div><span className="muted small">Patient</span><strong>{referral.patient}</strong></div><span className={referral.status === "DECLINED" ? "badge" : "status-pill"}>{referral.status}</span></div>}</article>}

    <article className="card"><h2>Follow-up / return visit / doctor appointment</h2><p className="muted">After today's care, schedule a future return date or book the patient directly with a doctor.</p><div className="form-grid"><label>Return date & time<input type="datetime-local" value={appointmentDate} onChange={(e) => setAppointmentDate(e.target.value)} /></label><label>Visit type<select><option>Doctor follow-up</option><option>Routine review</option><option>Post-discharge review</option><option>Maternal follow-up</option></select></label></div><div className="demo-actions"><button onClick={() => { setAppointmentBooked(true); setMessage(`Appointment booked for ${new Date(appointmentDate).toLocaleString()}.`); }}>Book doctor appointment</button><button className="button secondary" onClick={() => { setAppointmentBooked(true); setMessage(`Patient scheduled to return on ${new Date(appointmentDate).toLocaleString()}.`); }}>Schedule return visit</button></div>{appointmentBooked && <div className="success-box">APPOINTMENT BOOKED · {new Date(appointmentDate).toLocaleString()} · Doctor follow-up</div>}</article>

    <article className="card"><h2>9. Itemised billing</h2><p className="muted">Every service or medicine has its own quantity and standalone unit price. The total is calculated from the entered amounts.</p><div>{billing.map((line) => <div className="billing-line" key={line.id}><label>Description<input value={line.description} onChange={(e) => setBilling((current) => current.map((x) => x.id === line.id ? { ...x, description: e.target.value } : x))} /></label><label>Qty<input type="number" min="1" value={line.quantity} onChange={(e) => setBilling((current) => current.map((x) => x.id === line.id ? { ...x, quantity: Number(e.target.value) } : x))} /></label><label>Unit price (KES)<input type="number" min="0" value={line.price} onChange={(e) => updatePrice(line.id, Number(e.target.value))} /></label><strong>KES {(line.quantity * line.price).toLocaleString()}</strong></div>)}</div><div className="demo-actions"><button className="button secondary" onClick={() => setBilling((current) => [...current, { id: crypto.randomUUID(), description: "Additional clinical service", quantity: 1, price: 500 }])}>+ Add charge</button></div><div className="billing-total">Total: KES {total.toLocaleString()}</div></article>

    <article className="card"><h2>10–12. SHA claim · submission · reconciliation</h2><div className="patient-verification"><div><span className="muted small">Total claim</span><strong>KES {total.toLocaleString()}</strong></div><div><span className="muted small">Claim</span><strong>{claim}</strong></div><div><span className="muted small">Reconciliation</span><strong>{reconciled ? "NO VARIANCE" : "PENDING"}</strong></div></div><div className="demo-actions">{claim === "PENDING" && <button onClick={() => { setClaim("READY"); setMessage("Claim validated from itemised encounter charges."); }}>Create SHA claim</button>}{claim === "READY" && <button onClick={() => { setClaim("SUBMITTED"); setMessage("Claim submitted to the payer queue."); }}>Submit claim</button>}{claim === "SUBMITTED" && !reconciled && <button onClick={() => { setReconciled(true); setMessage("Payer response recorded. Claim reconciled with no variance."); }}>Record payment & reconcile</button>}{reconciled && <span className="success-box">CLAIM PAID · RECONCILED · KES {total.toLocaleString()}</span>}</div></article>

    {message && <div className="card info-box">{message}</div>}
    <article className="card warning-box"><strong>Demo boundary</strong><p>This walkthrough is controlled demonstration data. It does not contact live SHA, another hospital, or a real pharmacy. The production application already has secured referral/transfer and appointment backend foundations; the UI demo makes the complete stakeholder journey visible without pretending these demo clicks are live external transactions.</p></article>
  </section>;
}
