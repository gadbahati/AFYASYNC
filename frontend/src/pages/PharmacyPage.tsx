import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Medication = { id: string; code: string; name: string; strength: string | null; form: string | null; status: string };
type InventoryItem = { id: string; facility_id: string; medication_id: string; current_quantity: number; minimum_quantity: number; status: string };
type Prescription = { id: string; prescription_id: string; encounter_id: string; patient_id: string; status: string; created_at: string };

export function PharmacyPage() {
  const auth = useAuth();
  const [meds, setMeds] = useState<Medication[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ code: "", name: "", strength: "", form: "", generic_name: "", unit: "" });
  const [receipt, setReceipt] = useState({ medication_id: "", batch_number: "", expiry_date: "", quantity: "", purchase_price: "", selling_price: "" });

  function load() {
    setLoading(true); setError(null);
    Promise.all([api.listMedications(), api.listPharmacyInventory(), api.listPrescriptions()]).then(([m, inv, rx]) => { setMeds(m); setInventory(inv); setPrescriptions(rx); }).catch(e => setError(e instanceof ApiError ? e.code : "PHARMACY_LOAD_FAILED")).finally(() => setLoading(false));
  }
  useEffect(() => { load(); }, []);

  async function onAddMed(e: FormEvent) { e.preventDefault(); setBusy(true); setError(null); setMessage(""); try { await api.createMedication({ code: form.code.trim().toUpperCase(), name: form.name.trim(), strength: form.strength.trim() || null, form: form.form.trim() || null, generic_name: form.generic_name.trim() || null, unit: form.unit.trim() || null }); setForm({ code: "", name: "", strength: "", form: "", generic_name: "", unit: "" }); setMessage("Medication added to the live catalogue."); load(); } catch (e) { setError(e instanceof ApiError ? e.code : "CREATE_MED_FAILED"); } finally { setBusy(false); } }
  async function onReceive(e: FormEvent) { e.preventDefault(); if (!auth.facilityId) return; setBusy(true); setError(null); setMessage(""); try { await api.receiveInventory({ facility_id: auth.facilityId, medication_id: receipt.medication_id, batch_number: receipt.batch_number.trim(), expiry_date: receipt.expiry_date, quantity: Number(receipt.quantity), purchase_price: Number(receipt.purchase_price), selling_price: Number(receipt.selling_price) }); setReceipt({ medication_id: "", batch_number: "", expiry_date: "", quantity: "", purchase_price: "", selling_price: "" }); setMessage("Stock receipt posted. Quantity, batch, expiry and KES purchase/selling values are now recorded in the facility inventory ledger."); load(); } catch (e) { setError(e instanceof ApiError ? e.code : "INVENTORY_RECEIPT_FAILED"); } finally { setBusy(false); } }

  return <section className="page-stack"><header className="page-heading"><div><p className="eyebrow">Medication workflow</p><h1>Pharmacy</h1><p className="muted">Live medicine catalogue, receiving, facility stock and prescriptions. Every stock receipt is facility-scoped and auditable.</p></div><button type="button" className="button secondary" onClick={load}>Refresh</button></header>
    {error && <div className="error">{error}</div>}{message && <div className="success-box">{message}</div>}
    {loading ? <p>Loading pharmacy…</p> : <>
      <article className="card"><h2>Add medication to catalogue</h2><form className="form-grid" onSubmit={onAddMed}><label>Code<input required value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} /></label><label>Name<input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></label><label>Generic name<input value={form.generic_name} onChange={e => setForm({ ...form, generic_name: e.target.value })} /></label><label>Strength<input value={form.strength} onChange={e => setForm({ ...form, strength: e.target.value })} /></label><label>Form<input value={form.form} onChange={e => setForm({ ...form, form: e.target.value })} /></label><label>Unit<input value={form.unit} placeholder="tablet, bottle, vial…" onChange={e => setForm({ ...form, unit: e.target.value })} /></label><div className="full actions"><button type="submit" disabled={busy}>{busy ? "Saving…" : "Add to catalogue"}</button></div></form></article>
      <article className="card"><h2>Receive medicines into facility stock</h2><p className="muted">Record exactly what the hospital received, including quantity, batch, expiry and KES purchase/selling amounts.</p><form className="form-grid" onSubmit={onReceive}><label className="full">Medicine<select required value={receipt.medication_id} onChange={e => setReceipt({ ...receipt, medication_id: e.target.value })}><option value="">Select medicine</option>{meds.map(m => <option key={m.id} value={m.id}>{m.name} · {m.code} {m.strength ? `· ${m.strength}` : ""}</option>)}</select></label><label>Batch number<input required value={receipt.batch_number} onChange={e => setReceipt({ ...receipt, batch_number: e.target.value })} /></label><label>Expiry date<input required type="date" value={receipt.expiry_date} onChange={e => setReceipt({ ...receipt, expiry_date: e.target.value })} /></label><label>Quantity received<input required type="number" min="0.01" step="0.01" value={receipt.quantity} onChange={e => setReceipt({ ...receipt, quantity: e.target.value })} /></label><label>Purchase amount / unit (KES)<input required type="number" min="0" step="0.01" value={receipt.purchase_price} onChange={e => setReceipt({ ...receipt, purchase_price: e.target.value })} /></label><label>Selling amount / unit (KES)<input required type="number" min="0" step="0.01" value={receipt.selling_price} onChange={e => setReceipt({ ...receipt, selling_price: e.target.value })} /></label><div className="full actions"><button type="submit" disabled={busy || !receipt.medication_id}>{busy ? "Posting…" : "Post stock receipt"}</button></div></form></article>
      <article className="card"><h2>Catalogue ({meds.length})</h2><div className="table-wrap"><table><thead><tr><th>Code</th><th>Name</th><th>Strength</th><th>Form</th><th>Unit</th><th>Status</th></tr></thead><tbody>{meds.map(m => <tr key={m.id}><td>{m.code}</td><td>{m.name}</td><td>{m.strength || "—"}</td><td>{m.form || "—"}</td><td>—</td><td>{m.status}</td></tr>)}{meds.length === 0 && <tr><td colSpan={6} className="muted">No medications in the live catalogue.</td></tr>}</tbody></table></div></article>
      <article className="card"><h2>Facility inventory ({inventory.length})</h2><div className="table-wrap"><table><thead><tr><th>Medication ID</th><th>Current quantity</th><th>Minimum</th><th>Status</th></tr></thead><tbody>{inventory.map(i => <tr key={i.id}><td>{i.medication_id}</td><td>{i.current_quantity}</td><td>{i.minimum_quantity}</td><td>{i.status}</td></tr>)}{inventory.length === 0 && <tr><td colSpan={4} className="muted">No stock received yet.</td></tr>}</tbody></table></div></article>
      <article className="card"><h2>Prescriptions awaiting pharmacy ({prescriptions.length})</h2><div className="table-wrap"><table><thead><tr><th>Prescription</th><th>Patient</th><th>Encounter</th><th>Status</th><th>Created</th></tr></thead><tbody>{prescriptions.map(p => <tr key={p.id}><td>{p.prescription_id}</td><td>{p.patient_id}</td><td>{p.encounter_id}</td><td><span className="status-pill">{p.status}</span></td><td>{new Date(p.created_at).toLocaleString()}</td></tr>)}{prescriptions.length === 0 && <tr><td colSpan={5} className="muted">No prescriptions for this facility.</td></tr>}</tbody></table></div></article>
    </>}
  </section>;
}
