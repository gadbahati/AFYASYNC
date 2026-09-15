import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { getAccessToken } from "../auth/storage";
import { useAuth } from "../auth/AuthContext";

type Medication = { id: string; code: string; name: string; strength: string | null; form: string | null; status: string };
type InventoryItem = { id: string; facility_id: string; medication_id: string; current_quantity: number; minimum_quantity: number; status: string };
type Prescription = { id: string; prescription_id: string; encounter_id: string; patient_id: string; status: string; created_at: string };
type BillingService = { id: string; code: string; name: string; service_type: string; price: number; status: string };

export function PharmacyPage() {
  const auth = useAuth();
  const [params] = useSearchParams();
  const patientId = params.get("patientId") || "";
  const encounterId = params.get("encounterId") || "";
  const [meds, setMeds] = useState<Medication[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [services, setServices] = useState<BillingService[]>([]);
  const [patientName, setPatientName] = useState("");
  const [patientAfyaId, setPatientAfyaId] = useState("");
  const [record, setRecord] = useState<any>(null);
  const [selectedRxId, setSelectedRxId] = useState("");
  const [serviceByItem, setServiceByItem] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ code: "", name: "", strength: "", form: "", generic_name: "", unit: "" });
  const [receipt, setReceipt] = useState({ medication_id: "", batch_number: "", expiry_date: "", quantity: "", purchase_price: "", selling_price: "" });

  const selectedRx = useMemo(() => record?.prescriptions?.find((p: any) => p.id === selectedRxId), [record, selectedRxId]);
  const payable = useMemo(() => record?.billing?.payments?.filter((p: any) => p.status === "CONFIRMED").reduce((s: number, p: any) => s + Number(p.amount || 0), 0) ?? 0, [record]);
  const charges = useMemo(() => record?.billing?.charges?.filter((c: any) => c.encounter_id === (encounterId || selectedRx?.encounter_id)).reduce((s: number, c: any) => s + Number(c.total_amount || 0), 0) ?? 0, [record, encounterId, selectedRx]);

  async function load() {
    setLoading(true); setError(null);
    try {
      const [m, inv, rx, svc] = await Promise.all([api.listMedications(), api.listPharmacyInventory(), api.listPrescriptions(), api.listBillingServices()]);
      setMeds(m); setInventory(inv); setPrescriptions(rx); setServices(svc);
      if (patientId) {
        const r = await api.getPatientRecord(patientId);
        setRecord(r);
        const p = r.patient;
        setPatientName([p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" "));
        setPatientAfyaId(p.afya_id);
        const matching = r.prescriptions.find((x: any) => (!encounterId || x.encounter_id === encounterId) && x.status !== "DISPENSED") || r.prescriptions.find((x: any) => x.status !== "DISPENSED");
        if (matching) setSelectedRxId(matching.id);
      }
    } catch (e) { setError(e instanceof ApiError ? e.code : "PHARMACY_LOAD_FAILED"); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, [patientId, encounterId]);

  async function onAddMed(e: FormEvent) { e.preventDefault(); setBusy(true); setError(null); setMessage(""); try { await api.createMedication({ code: form.code.trim().toUpperCase(), name: form.name.trim(), strength: form.strength.trim() || null, form: form.form.trim() || null, generic_name: form.generic_name.trim() || null, unit: form.unit.trim() || null }); setForm({ code: "", name: "", strength: "", form: "", generic_name: "", unit: "" }); setMessage("Medication added to the live catalogue."); await load(); } catch (e) { setError(e instanceof ApiError ? e.code : "CREATE_MED_FAILED"); } finally { setBusy(false); } }
  async function onReceive(e: FormEvent) { e.preventDefault(); if (!auth.facilityId) return; setBusy(true); setError(null); setMessage(""); try { await api.receiveInventory({ facility_id: auth.facilityId, medication_id: receipt.medication_id, batch_number: receipt.batch_number.trim(), expiry_date: receipt.expiry_date, quantity: Number(receipt.quantity), purchase_price: Number(receipt.purchase_price), selling_price: Number(receipt.selling_price) }); setReceipt({ medication_id: "", batch_number: "", expiry_date: "", quantity: "", purchase_price: "", selling_price: "" }); setMessage("Stock receipt posted to the facility inventory ledger."); await load(); } catch (e) { setError(e instanceof ApiError ? e.code : "INVENTORY_RECEIPT_FAILED"); } finally { setBusy(false); } }

  async function dispense() {
    if (!selectedRx) return;
    const billingItems = selectedRx.items.map((item: any) => ({ prescription_item_id: item.id, service_id: serviceByItem[item.id] })).filter((x: any) => x.service_id);
    if (billingItems.length !== selectedRx.items.length) { setError("SELECT_BILLING_SERVICE_FOR_EACH_MEDICINE"); return; }
    if (charges > 0 && payable < charges) { setError("PAYMENT_REQUIRED_BEFORE_DISPENSING"); return; }
    setBusy(true); setError(null); setMessage("");
    try {
      const base = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
      const token = getAccessToken();
      const res = await fetch(`${base}/api/v1/pharmacy/prescriptions/${selectedRx.id}/dispense`, { method: "POST", headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) }, body: JSON.stringify({ billing_items: billingItems }) });
      if (!res.ok) { let body: any = null; try { body = await res.json(); } catch {} throw new Error(body?.detail || "DISPENSE_FAILED"); }
      const result = await res.json();
      setMessage(`Dispensed successfully. ${result.movements_created} stock movement(s) recorded and ${result.charges_created} billing charge(s) linked to the prescription.`);
      await load();
    } catch (e) { setError(e instanceof ApiError ? e.code : e instanceof Error ? e.message : "DISPENSE_FAILED"); }
    finally { setBusy(false); }
  }

  return <section className="page-stack pharmacy-page">
    <header className="page-heading"><div><p className="eyebrow">Medication workflow</p><h1>Pharmacy</h1><p className="muted">Receive the named patient, verify the encounter and payment, dispense the prescription, and record stock movement against the same care journey.</p></div><button type="button" className="button secondary" onClick={() => void load()}>Refresh</button></header>
    {patientId && <section className="card patient-context"><div><p className="eyebrow">Patient at pharmacy</p><h2>{patientName || "Loading patient…"}</h2><p className="muted">{patientAfyaId} {encounterId ? `· Encounter ${encounterId}` : ""}</p></div><div className="actions"><Link className="button secondary" to={`/patients/${patientId}/journey`}>Open care journey</Link><span className="status-pill">RECEIVED FOR PHARMACY</span></div><div className="pharmacy-payment"><span>Recorded charges</span><strong>KES {charges.toLocaleString()}</strong><span>Confirmed payments</span><strong>KES {payable.toLocaleString()}</strong></div></section>}
    {error && <div className="error">{error}</div>}{message && <div className="success-box">{message}</div>}
    {loading ? <p>Loading pharmacy…</p> : <>
      {patientId && <article className="card"><div className="row-between"><div><p className="eyebrow">Patient-specific dispensing</p><h2>Prescription for {patientName}</h2><p className="muted">Only this patient's prescription is shown here when opened from the care journey. Each item must map to a billing service before dispensing.</p></div>{selectedRx && <span className="status-pill">{selectedRx.status}</span>}</div>
        {!selectedRx ? <div className="notice"><strong>No undispensed prescription found.</strong><p>Return to the clinical encounter and create a prescription before sending this patient to pharmacy.</p><Link className="button secondary" to={encounterId ? `/encounters/${encounterId}` : `/patients/${patientId}/journey`}>Return to clinical care</Link></div> : <>
          <div className="table-wrap"><table><thead><tr><th>Medicine</th><th>Directions</th><th>Quantity</th><th>Billing service</th></tr></thead><tbody>{selectedRx.items.map((item: any) => <tr key={item.id}><td><strong>{item.name} {item.strength || ""}</strong></td><td>{item.dose} · {item.frequency} · {item.duration}{item.route ? ` · ${item.route}` : ""}<br /><small>{item.instructions || "No additional instructions"}</small></td><td>{item.quantity}</td><td><select value={serviceByItem[item.id] || ""} onChange={e => setServiceByItem(c => ({ ...c, [item.id]: e.target.value }))}><option value="">Select pharmacy billing service</option>{services.filter(s => s.status === "ACTIVE").map(s => <option key={s.id} value={s.id}>{s.name} · KES {Number(s.price).toLocaleString()}</option>)}</select></td></tr>)}</tbody></table></div>
          <div className="notice"><strong>Dispensing gate</strong><p>Payment is checked before dispensing when the encounter has recorded charges. The server also re-validates prescription, encounter, facility, stock and billing requirements before posting stock movements.</p><button className="button" type="button" disabled={busy || selectedRx.status === "DISPENSED"} onClick={() => void dispense()}>{busy ? "Processing…" : "Receive & dispense patient"}</button></div>
        </>}</article>}

      <article className="card"><h2>Prescriptions awaiting pharmacy ({prescriptions.length})</h2><div className="table-wrap"><table><thead><tr><th>Prescription</th><th>Patient</th><th>Encounter</th><th>Status</th><th>Action</th></tr></thead><tbody>{prescriptions.map(p => <tr key={p.id}><td>{p.prescription_id}</td><td>{p.patient_id}</td><td>{p.encounter_id}</td><td><span className="status-pill">{p.status}</span></td><td><Link className="button secondary" to={`/patients/${p.patient_id}/journey?encounterId=${p.encounter_id}`}>Open patient journey</Link></td></tr>)}{prescriptions.length === 0 && <tr><td colSpan={5} className="muted">No prescriptions for this facility.</td></tr>}</tbody></table></div></article>
      <article className="card"><h2>Receive medicines into facility stock</h2><p className="muted">Record quantity, batch, expiry and actual KES purchase/selling amounts. This is separate from dispensing patient medicines.</p><form className="form-grid" onSubmit={onReceive}><label className="full">Medicine<select required value={receipt.medication_id} onChange={e => setReceipt({ ...receipt, medication_id: e.target.value })}><option value="">Select medicine</option>{meds.map(m => <option key={m.id} value={m.id}>{m.name} · {m.code} {m.strength ? `· ${m.strength}` : ""}</option>)}</select></label><label>Batch number<input required value={receipt.batch_number} onChange={e => setReceipt({ ...receipt, batch_number: e.target.value })} /></label><label>Expiry date<input required type="date" value={receipt.expiry_date} onChange={e => setReceipt({ ...receipt, expiry_date: e.target.value })} /></label><label>Quantity received<input required type="number" min="0.01" step="0.01" value={receipt.quantity} onChange={e => setReceipt({ ...receipt, quantity: e.target.value })} /></label><label>Purchase / unit (KES)<input required type="number" min="0" step="0.01" value={receipt.purchase_price} onChange={e => setReceipt({ ...receipt, purchase_price: e.target.value })} /></label><label>Selling / unit (KES)<input required type="number" min="0" step="0.01" value={receipt.selling_price} onChange={e => setReceipt({ ...receipt, selling_price: e.target.value })} /></label><div className="full actions"><button type="submit" disabled={busy || !receipt.medication_id}>{busy ? "Posting…" : "Post stock receipt"}</button></div></form></article>
      <article className="card"><h2>Facility inventory ({inventory.length})</h2><div className="table-wrap"><table><thead><tr><th>Medication ID</th><th>Current quantity</th><th>Minimum</th><th>Status</th></tr></thead><tbody>{inventory.map(i => <tr key={i.id}><td>{i.medication_id}</td><td>{i.current_quantity}</td><td>{i.minimum_quantity}</td><td>{i.status}</td></tr>)}{inventory.length === 0 && <tr><td colSpan={4} className="muted">No stock received yet.</td></tr>}</tbody></table></div></article>
    </>}
    <style>{`.pharmacy-page .patient-context{display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center}.pharmacy-page .pharmacy-payment{grid-column:1/-1;display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding-top:12px;border-top:1px solid var(--border-color,#d8e0e8)}.pharmacy-page .pharmacy-payment span{color:var(--muted,#667085)}.pharmacy-page .pharmacy-payment strong{margin-right:18px}@media(max-width:760px){.pharmacy-page .patient-context{display:block}.pharmacy-page .patient-context .actions{margin-top:12px}.pharmacy-page .pharmacy-payment{margin-top:12px}}`}</style>
  </section>;
}
