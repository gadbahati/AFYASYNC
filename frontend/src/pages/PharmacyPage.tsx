import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";

type Medication = { id: string; code: string; name: string; strength: string | null; form: string | null; status: string };
type InventoryItem = { id: string; facility_id: string; medication_id: string; current_quantity: number; minimum_quantity: number; status: string };
type Prescription = { id: string; prescription_id: string; encounter_id: string; patient_id: string; status: string; created_at: string };

export function PharmacyPage() {
  const [meds, setMeds] = useState<Medication[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ code: "", name: "", strength: "", form: "" });
  const [busy, setBusy] = useState(false);

  function load() {
    setLoading(true);
    setError(null);
    Promise.all([
      api.listMedications().catch(() => [] as Medication[]),
      api.listPharmacyInventory().catch(() => [] as InventoryItem[]),
      api.listPrescriptions().catch(() => [] as Prescription[]),
    ])
      .then(([m, inv, rx]) => {
        setMeds(m);
        setInventory(inv);
        setPrescriptions(rx);
      })
      .catch((e) => setError(e instanceof ApiError ? e.code : "PHARMACY_LOAD_FAILED"))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function onAddMed(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.createMedication({
        code: form.code.trim().toUpperCase(),
        name: form.name.trim(),
        strength: form.strength.trim() || null,
        form: form.form.trim() || null,
      });
      setForm({ code: "", name: "", strength: "", form: "" });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "CREATE_MED_FAILED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Medication workflow</p>
          <h1>Pharmacy</h1>
          <p className="muted">Live medication catalogue, facility inventory and prescriptions from the AfyaSync API.</p>
        </div>
        <button type="button" className="button secondary" onClick={load}>Refresh</button>
      </header>
      {error && <div className="error">{error}</div>}
      {loading ? <p>Loading pharmacy…</p> : (
        <>
          <article className="card">
            <h2>Add medication</h2>
            <form className="form-grid" onSubmit={onAddMed}>
              <label>Code<input required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} /></label>
              <label>Name<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
              <label>Strength<input value={form.strength} onChange={(e) => setForm({ ...form, strength: e.target.value })} /></label>
              <label>Form<input value={form.form} onChange={(e) => setForm({ ...form, form: e.target.value })} /></label>
              <div className="full actions"><button type="submit" disabled={busy}>{busy ? "Saving…" : "Create medication"}</button></div>
            </form>
          </article>
          <article className="card">
            <h2>Catalogue ({meds.length})</h2>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Code</th><th>Name</th><th>Strength</th><th>Form</th><th>Status</th></tr></thead>
                <tbody>
                  {meds.map((m) => (
                    <tr key={m.id}><td>{m.code}</td><td>{m.name}</td><td>{m.strength || "—"}</td><td>{m.form || "—"}</td><td>{m.status}</td></tr>
                  ))}
                  {meds.length === 0 && <tr><td colSpan={5} className="muted">No medications yet. Add the first catalogue item above.</td></tr>}
                </tbody>
              </table>
            </div>
          </article>
          <article className="card">
            <h2>Facility inventory ({inventory.length})</h2>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Medication ID</th><th>Qty</th><th>Min</th><th>Status</th></tr></thead>
                <tbody>
                  {inventory.map((i) => (
                    <tr key={i.id}><td>{i.medication_id}</td><td>{i.current_quantity}</td><td>{i.minimum_quantity}</td><td>{i.status}</td></tr>
                  ))}
                  {inventory.length === 0 && <tr><td colSpan={4} className="muted">No stock received yet. Receive inventory batches through the pharmacy API.</td></tr>}
                </tbody>
              </table>
            </div>
          </article>
          <article className="card">
            <h2>Prescriptions ({prescriptions.length})</h2>
            <div className="table-wrap">
              <table>
                <thead><tr><th>RX</th><th>Patient</th><th>Encounter</th><th>Status</th><th>Created</th></tr></thead>
                <tbody>
                  {prescriptions.map((p) => (
                    <tr key={p.id}>
                      <td>{p.prescription_id}</td>
                      <td>{p.patient_id}</td>
                      <td>{p.encounter_id}</td>
                      <td><span className="status-pill">{p.status}</span></td>
                      <td>{new Date(p.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                  {prescriptions.length === 0 && <tr><td colSpan={5} className="muted">No prescriptions for this facility.</td></tr>}
                </tbody>
              </table>
            </div>
          </article>
        </>
      )}
    </section>
  );
}
