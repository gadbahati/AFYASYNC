import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { FeatureListPage } from "./FeatureListPage";
import type { LabTest, Referral } from "../api/types";
import "./lab.css";

export function LabPage() {
  const [catalogue, setCatalogue] = useState<LabTest[]>([]);
  const [selected, setSelected] = useState<string[]>(["lt1", "lt2"]);
  const [results, setResults] = useState<Record<string, string>>({ lt1: "Hb 12.8 g/dL; WBC 7.2 ×10⁹/L; Platelets 286 ×10⁹/L", lt2: "Negative" });
  const [performed, setPerformed] = useState<string[]>(["lt1", "lt2"]);
  const [forwarded, setForwarded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listLabTests().then(setCatalogue).catch((e) => setError(e instanceof ApiError ? e.code : "LAB_CATALOGUE_FAILED")).finally(() => setLoading(false));
  }, []);

  const selectedTests = catalogue.filter((test) => selected.includes(test.id));
  const total = selectedTests.reduce((sum, test) => sum + Number(test.price || 0), 0);
  const completed = selectedTests.filter((test) => performed.includes(test.id) && results[test.id]?.trim()).length;

  function toggleTest(id: string) {
    setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
    setForwarded(false);
  }

  function markPerformed(id: string) {
    setPerformed((current) => current.includes(id) ? current : [...current, id]);
  }

  return <section className="page-stack">
    <header className="page-heading"><div><p className="eyebrow">Laboratory information system</p><h1>Laboratory</h1><p className="muted">Professional diagnostic workflow: order individual tests, document each examination, capture results, calculate charges and forward verified findings for clinical prescription review.</p></div><span className="status-pill">DEMO WORKFLOW</span></header>
    {error && <div className="error">{error}</div>}
    {loading ? <p>Loading laboratory catalogue…</p> : <>
      <article className="card">
        <div className="row-between"><div><h2>1. Test order</h2><p className="muted">Choose individual examinations. Each test has its own description, specimen requirement and price.</p></div><div><small>Laboratory total</small><h2>KES {total.toLocaleString()}</h2></div></div>
        <div className="lab-test-grid">{catalogue.map((test) => <label className={selected.includes(test.id) ? "lab-test-card selected" : "lab-test-card"} key={test.id}><input type="checkbox" checked={selected.includes(test.id)} onChange={() => toggleTest(test.id)} /><div><div className="row-between"><strong>{test.name}</strong><strong>KES {Number(test.price).toLocaleString()}</strong></div><p className="muted">{test.code} · {test.category || "General laboratory"}</p><p>{test.description || "Laboratory examination."}</p><small>Specimen: {test.sample_type || "Not specified"}</small></div></label>)}</div>
      </article>

      <article className="card">
        <div className="row-between"><div><h2>2. Individual test records</h2><p className="muted">Each examination is written down independently so the clinical record shows exactly what was requested and performed.</p></div><span className="status-pill">{completed}/{selectedTests.length} COMPLETED</span></div>
        <div className="table-wrap"><table><thead><tr><th>Test / code</th><th>Description</th><th>Specimen</th><th>Price</th><th>Result / observation</th><th>Workflow</th></tr></thead><tbody>{selectedTests.map((test) => <tr key={test.id}><td><strong>{test.name}</strong><br /><small>{test.code}</small></td><td>{test.description || "Laboratory examination"}</td><td>{test.sample_type || "—"}</td><td><strong>KES {Number(test.price).toLocaleString()}</strong></td><td><input value={results[test.id] || ""} placeholder="Enter measured result / observation" onChange={(e) => { setResults((current) => ({ ...current, [test.id]: e.target.value })); setForwarded(false); }} /></td><td>{performed.includes(test.id) ? <span className="status-pill">RESULT RECORDED</span> : <button onClick={() => markPerformed(test.id)}>Mark performed</button>}</td></tr>)}</tbody></table></div>
      </article>

      <article className="card">
        <h2>3. Laboratory billing</h2>
        <p className="muted">Every completed test contributes its own standalone laboratory charge.</p>
        <div className="lab-summary">{selectedTests.map((test) => <div className="billing-line" key={test.id}><div><strong>{test.name}</strong><p className="muted">{performed.includes(test.id) ? "Performed" : "Pending"}</p></div><strong>KES {Number(test.price).toLocaleString()}</strong></div>)}</div>
        <div className="billing-total">Laboratory total: KES {total.toLocaleString()}</div>
      </article>

      <article className="card">
        <div className="row-between"><div><h2>4. Review & forward to prescription</h2><p className="muted">Completed results are forwarded to the authorized clinician for review. The system does not automatically prescribe medication from a laboratory result.</p></div><strong>{completed}/{selectedTests.length} results ready</strong></div>
        <div className="lab-summary">{selectedTests.map((test) => <div className="billing-line" key={test.id}><div><strong>{test.name}</strong><p className="muted">{results[test.id] || "Result pending"}</p></div><span className={performed.includes(test.id) && results[test.id]?.trim() ? "status-pill" : "badge"}>{performed.includes(test.id) && results[test.id]?.trim() ? "READY" : "PENDING"}</span></div>)}</div>
        <div className="form-actions"><button disabled={selectedTests.length === 0 || completed !== selectedTests.length} onClick={() => setForwarded(true)}>{forwarded ? "Forwarded to prescription review" : "Forward results to prescription review"}</button>{forwarded && <span className="success-box">✓ All individual tests recorded · results forwarded to clinician · laboratory charges KES {total.toLocaleString()}</span>}</div>
      </article>
    </>}
  </section>;
}

export function PharmacyPage() {
  const [dispensed, setDispensed] = useState(false);
  return <section className="page-stack"><header className="page-heading"><div><p className="eyebrow">Medication workflow</p><h1>Pharmacy</h1><p className="muted">Receive prescriptions, dispense from stock and mark the patient ready for release.</p></div></header><article className="card"><div className="row-between"><div><strong>RX-501 · Amina Wanjiku</strong><p className="muted">Paracetamol 500 mg × 20 · Amoxicillin 500 mg × 21</p></div><span className={dispensed ? "status-pill" : "badge"}>{dispensed ? "DISPENSED" : "PENDING"}</span></div><div className="form-actions"><button disabled={dispensed} onClick={() => setDispensed(true)}>{dispensed ? "Dispensed" : "Receive & dispense"}</button>{dispensed && <span className="success-box">Stock deducted · Patient RELEASED / ready for discharge</span>}</div></article></section>;
}

export function BillingPage() {
  const [lines, setLines] = useState([{ id: "1", description: "Doctor consultation", qty: 1, price: 850 }, { id: "2", description: "Paracetamol 500 mg", qty: 20, price: 5 }]);
  const total = lines.reduce((sum, x) => sum + x.qty * x.price, 0);
  return <section className="page-stack"><header className="page-heading"><div><p className="eyebrow">Financial workflow</p><h1>Billing</h1><p className="muted">Every clinical service and medicine has its own standalone unit price. Invoice totals are calculated from quantity × price.</p></div></header><article className="card"><h2>Encounter charges</h2>{lines.map((line) => <div className="billing-line" key={line.id}><label>Description<input value={line.description} onChange={(e) => setLines((c) => c.map((x) => x.id === line.id ? { ...x, description: e.target.value } : x))} /></label><label>Qty<input type="number" min="1" value={line.qty} onChange={(e) => setLines((c) => c.map((x) => x.id === line.id ? { ...x, qty: Number(e.target.value) } : x))} /></label><label>Unit price (KES)<input type="number" min="0" value={line.price} onChange={(e) => setLines((c) => c.map((x) => x.id === line.id ? { ...x, price: Number(e.target.value) } : x))} /></label><strong>KES {(line.qty * line.price).toLocaleString()}</strong></div>)}<div className="form-actions"><button className="button secondary" onClick={() => setLines((c) => [...c, { id: crypto.randomUUID(), description: "Additional service", qty: 1, price: 500 }])}>+ Add service / medicine</button></div><div className="billing-total">Total: KES {total.toLocaleString()}</div></article></section>;
}

export function ClaimsPage() {
  return <FeatureListPage title="Claims" subtitle="Payer claim submission and reconciliation" columns={[{ key: "claim", label: "Claim" }, { key: "patient", label: "Patient" }, { key: "amount", label: "Amount (KES)" }, { key: "payer", label: "Payer" }, { key: "status", label: "Status" }]} rows={[{ claim: "CLM-3001", patient: "Amina Wanjiku", amount: "2,500", payer: "SHA", status: "SUBMITTED" }, { claim: "CLM-3002", patient: "Faith Mwangi", amount: "3,800", payer: "SHA", status: "APPROVED" }, { claim: "CLM-3003", patient: "Brian Ochieng", amount: "900", payer: "SHA", status: "PAID" }]} />;
}

export function ReferralsPage() {
  const [rows, setRows] = useState<Referral[]>([]);
  const [role, setRole] = useState<"all" | "source" | "destination">("all");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const load = () => { setLoading(true); api.listReferrals(role).then((r) => setRows(r.items)).catch((e) => setError(e instanceof ApiError ? e.code : "LOAD_FAILED")).finally(() => setLoading(false)); };
  useEffect(() => { load(); }, [role]);
  async function decide(id: string, status: "ACCEPTED" | "DECLINED") { try { const updated = await api.updateReferralStatus(id, status); setRows((c) => c.map((r) => r.id === id ? updated : r)); } catch (e) { setError(e instanceof ApiError ? e.code : "UPDATE_FAILED"); } }
  return <section className="page-stack"><header className="page-heading"><div><p className="eyebrow">Continuity & transfer</p><h1>Referrals & transfers</h1><p className="muted">The sending facility creates a referral. The receiving facility can accept or decline it.</p></div><div className="form-actions"><button className={role === "all" ? "button" : "button secondary"} onClick={() => setRole("all")}>All</button><button className={role === "source" ? "button" : "button secondary"} onClick={() => setRole("source")}>Sent</button><button className={role === "destination" ? "button" : "button secondary"} onClick={() => setRole("destination")}>Receiving</button></div></header>{error && <div className="error">{error}</div>}{loading ? <p>Loading…</p> : <div className="table-wrap"><table><thead><tr><th>Referral</th><th>Patient</th><th>From</th><th>To</th><th>Reason</th><th>Status</th><th>Receiving action</th></tr></thead><tbody>{rows.map((r) => <tr key={r.id}><td>{r.referral_id}</td><td>{r.patient_id}</td><td>{r.source_facility_id}</td><td>{r.destination_facility_id}</td><td>{r.reason}</td><td><span className={r.status === "DECLINED" ? "badge" : "status-pill"}>{r.status}</span></td><td>{r.status === "SENT" || r.status === "CREATED" ? <div className="form-actions"><button onClick={() => decide(r.id, "ACCEPTED")}>Accept</button><button className="button secondary" onClick={() => decide(r.id, "DECLINED")}>Decline</button></div> : <span className="muted">No action</span>}</td></tr>)}{rows.length === 0 && <tr><td colSpan={7} className="muted">No referrals for this facility.</td></tr>}</tbody></table></div>}</section>;
}
