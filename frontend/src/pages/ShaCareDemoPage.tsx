import { useMemo, useState } from "react";

const DEMO_MEMBERS = [
  {
    number: "SHA-0019283746",
    name: "Amina Wanjiku",
    dob: "12 Apr 1992",
    sex: "Female",
    status: "ACTIVE",
    package: "MCH + Inpatient",
    phone: "+254 712 000 001",
  },
  {
    number: "SHA-0048172930",
    name: "Brian Otieno Ochieng",
    dob: "03 Nov 1985",
    sex: "Male",
    status: "ACTIVE",
    package: "Inpatient",
    phone: "+254 712 000 002",
  },
];

const MEDICINES = [
  { id: "amox", name: "Amoxicillin 500 mg", stock: 84, unit: "capsules" },
  { id: "para", name: "Paracetamol 500 mg", stock: 240, unit: "tablets" },
  { id: "iron", name: "Ferrous Sulphate 200 mg", stock: 120, unit: "tablets" },
  { id: "folate", name: "Folic Acid 5 mg", stock: 96, unit: "tablets" },
  { id: "cef", name: "Ceftriaxone 1 g", stock: 30, unit: "vials" },
];

type PrescriptionLine = {
  medicationId: string;
  dose: string;
  frequency: string;
  duration: string;
  quantity: number;
};

export function ShaCareDemoPage() {
  const [query, setQuery] = useState("");
  const [member, setMember] = useState<(typeof DEMO_MEMBERS)[number] | null>(null);
  const [admitted, setAdmitted] = useState(false);
  const [ward, setWard] = useState("General Ward");
  const [bed, setBed] = useState("G-12");
  const [diagnosis, setDiagnosis] = useState("Medical observation");
  const [prescription, setPrescription] = useState<PrescriptionLine[]>([]);
  const [selectedMedicine, setSelectedMedicine] = useState(MEDICINES[0].id);
  const [quantity, setQuantity] = useState(10);
  const [message, setMessage] = useState<string | null>(null);

  const selected = useMemo(
    () => MEDICINES.find((m) => m.id === selectedMedicine)!,
    [selectedMedicine],
  );

  function searchMember() {
    const normalized = query.trim().toLowerCase();
    const found = DEMO_MEMBERS.find((item) => item.number.toLowerCase() === normalized);
    setMember(found ?? null);
    setAdmitted(false);
    setMessage(found ? "SHA member verified for this demo facility." : "No SHA member found. Try SHA-0019283746.");
  }

  function startAdmission() {
    if (!member) return;
    setAdmitted(true);
    setMessage(`${member.name} admitted to ${ward}, bed ${bed}.`);
  }

  function addPrescription() {
    if (!member || !admitted) return;
    if (quantity < 1 || quantity > selected.stock) {
      setMessage(`Quantity must be between 1 and ${selected.stock}.`);
      return;
    }
    setPrescription((current) => [
      ...current,
      { medicationId: selected.id, dose: "1 unit", frequency: "TDS", duration: "5 days", quantity },
    ]);
    setMessage(`${selected.name} added to the prescription.`);
  }

  function dispense() {
    if (!prescription.length) return;
    setMessage(`Prescription sent to Pharmacy. ${prescription.length} medicine item(s) ready for dispensing.`);
  }

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Demonstration workflow</p>
          <h1>SHA patient → admission → pharmacy</h1>
          <p className="muted">A realistic walkthrough for stakeholder approval before production integration.</p>
        </div>
        <span className="badge">DEMO ONLY</span>
      </div>

      <article className="card">
        <div className="section-title-row">
          <div>
            <h2>1. Verify SHA member</h2>
            <p className="muted">Search the member number and load the patient's identity and benefit status.</p>
          </div>
        </div>
        <div className="form-grid">
          <label>
            SHA member / ID number
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. SHA-0019283746" onKeyDown={(e) => e.key === "Enter" && searchMember()} />
          </label>
          <div className="form-actions"><button type="button" onClick={searchMember}>Verify member</button></div>
        </div>
        {member && (
          <div className="patient-verification">
            <div><span className="muted small">Member</span><strong>{member.number}</strong></div>
            <div><span className="muted small">Patient</span><strong>{member.name}</strong></div>
            <div><span className="muted small">DOB / Sex</span><strong>{member.dob} · {member.sex}</strong></div>
            <div><span className="muted small">Benefit</span><strong>{member.package}</strong></div>
            <span className="status-pill">{member.status}</span>
          </div>
        )}
      </article>

      {member && (
        <article className="card">
          <h2>2. Start admission</h2>
          <p className="muted">Create the inpatient episode and assign the patient to a ward and bed.</p>
          <div className="form-grid">
            <label>Ward<select value={ward} onChange={(e) => setWard(e.target.value)}><option>General Ward</option><option>Maternity Ward</option><option>Paediatric Ward</option><option>Private Ward</option></select></label>
            <label>Bed<input value={bed} onChange={(e) => setBed(e.target.value)} /></label>
            <label className="span-2">Admission diagnosis<input value={diagnosis} onChange={(e) => setDiagnosis(e.target.value)} /></label>
          </div>
          {!admitted ? <button type="button" onClick={startAdmission}>Start admission</button> : <div className="success-box">Admission active · {ward} · Bed {bed} · {diagnosis}</div>}
        </article>
      )}

      {admitted && (
        <article className="card">
          <h2>3. Prescription</h2>
          <p className="muted">Select medicines from the facility pharmacy stock and add them to this admission.</p>
          <div className="form-grid">
            <label>Medicine<select value={selectedMedicine} onChange={(e) => setSelectedMedicine(e.target.value)}>{MEDICINES.map((m) => <option key={m.id} value={m.id}>{m.name} · {m.stock} {m.unit} in stock</option>)}</select></label>
            <label>Quantity<input type="number" min="1" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} /></label>
            <div className="form-actions"><button type="button" onClick={addPrescription}>Add medicine</button></div>
          </div>
          {prescription.length > 0 && (
            <div className="table-wrap">
              <table><thead><tr><th>Medicine</th><th>Dose</th><th>Frequency</th><th>Duration</th><th>Qty</th></tr></thead><tbody>
                {prescription.map((line, index) => <tr key={`${line.medicationId}-${index}`}><td>{MEDICINES.find((m) => m.id === line.medicationId)?.name}</td><td>{line.dose}</td><td>{line.frequency}</td><td>{line.duration}</td><td>{line.quantity}</td></tr>)}
              </tbody></table>
            </div>
          )}
          {prescription.length > 0 && <button type="button" className="button secondary" onClick={dispense}>Send prescription to Pharmacy</button>}
        </article>
      )}

      {message && <div className="card info-box">{message}</div>}

      <article className="card warning-box">
        <strong>Demo boundary</strong>
        <p>This walkthrough intentionally uses seeded demo members and pharmacy stock. It does not contact SHA or dispense real medicine. The production version will connect member verification, pre-authorisation, admissions, inventory and claims to the approved integrations.</p>
      </article>
    </section>
  );
}
