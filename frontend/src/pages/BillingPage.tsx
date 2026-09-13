import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";

type Service = { id: string; code: string; name: string; service_type: string; price: number; status: string };
type Invoice = { id: string; invoice_id: string; patient_id: string; encounter_id: string; total_amount: number; patient_amount: number; payer_amount: number; status: string };

const money = (n: number) => `KES ${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function BillingPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [svc, setSvc] = useState({ code: "", name: "", service_type: "CONSULTATION", price: "" });
  const [pay, setPay] = useState({ invoice_id: "", amount: "", payment_method: "CASH" });

  function load() {
    setLoading(true);
    setError(null);
    Promise.all([
      api.listBillingServices().catch(() => [] as Service[]),
      api.listInvoices().catch(() => [] as Invoice[]),
    ])
      .then(([s, inv]) => {
        setServices(s);
        setInvoices(inv);
      })
      .catch((e) => setError(e instanceof ApiError ? e.code : "BILLING_LOAD_FAILED"))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function onAddService(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.createBillingService({
        code: svc.code.trim().toUpperCase(),
        name: svc.name.trim(),
        service_type: svc.service_type,
        price: Number(svc.price),
      });
      setSvc({ code: "", name: "", service_type: "CONSULTATION", price: "" });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "SERVICE_CREATE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onPay(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.recordPayment({
        invoice_id: pay.invoice_id,
        amount: Number(pay.amount),
        payment_method: pay.payment_method,
      });
      setPay({ invoice_id: "", amount: "", payment_method: "CASH" });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "PAYMENT_FAILED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Financial workflow</p>
          <h1>Billing</h1>
          <p className="muted">Facility service catalogue, invoices and cash/other payments from the live API.</p>
        </div>
        <button type="button" className="button secondary" onClick={load}>Refresh</button>
      </header>
      {error && <div className="error">{error}</div>}
      {loading ? <p>Loading billing…</p> : (
        <>
          <article className="card">
            <h2>Add service</h2>
            <form className="form-grid" onSubmit={onAddService}>
              <label>Code<input required value={svc.code} onChange={(e) => setSvc({ ...svc, code: e.target.value })} /></label>
              <label>Name<input required value={svc.name} onChange={(e) => setSvc({ ...svc, name: e.target.value })} /></label>
              <label>Type
                <select value={svc.service_type} onChange={(e) => setSvc({ ...svc, service_type: e.target.value })}>
                  <option value="CONSULTATION">Consultation</option>
                  <option value="LAB">Lab</option>
                  <option value="PHARMACY">Pharmacy</option>
                  <option value="PROCEDURE">Procedure</option>
                  <option value="OTHER">Other</option>
                </select>
              </label>
              <label>Price (KES)<input required type="number" min="1" step="0.01" value={svc.price} onChange={(e) => setSvc({ ...svc, price: e.target.value })} /></label>
              <div className="full actions"><button type="submit" disabled={busy}>{busy ? "Saving…" : "Create service"}</button></div>
            </form>
          </article>
          <article className="card">
            <h2>Services ({services.length})</h2>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Code</th><th>Name</th><th>Type</th><th>Price</th><th>Status</th></tr></thead>
                <tbody>
                  {services.map((s) => (
                    <tr key={s.id}><td>{s.code}</td><td>{s.name}</td><td>{s.service_type}</td><td>{money(s.price)}</td><td>{s.status}</td></tr>
                  ))}
                  {services.length === 0 && <tr><td colSpan={5} className="muted">No services configured.</td></tr>}
                </tbody>
              </table>
            </div>
          </article>
          <article className="card">
            <h2>Invoices ({invoices.length})</h2>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Invoice</th><th>Patient</th><th>Encounter</th><th>Total</th><th>Patient</th><th>Payer</th><th>Status</th></tr></thead>
                <tbody>
                  {invoices.map((i) => (
                    <tr key={i.id}>
                      <td>{i.invoice_id}</td>
                      <td>{i.patient_id}</td>
                      <td>{i.encounter_id}</td>
                      <td>{money(i.total_amount)}</td>
                      <td>{money(i.patient_amount)}</td>
                      <td>{money(i.payer_amount)}</td>
                      <td><span className="status-pill">{i.status}</span></td>
                    </tr>
                  ))}
                  {invoices.length === 0 && <tr><td colSpan={7} className="muted">No invoices yet. Create from encounter charges.</td></tr>}
                </tbody>
              </table>
            </div>
          </article>
          <article className="card">
            <h2>Record payment</h2>
            <form className="form-grid" onSubmit={onPay}>
              <label className="full">Invoice
                <select required value={pay.invoice_id} onChange={(e) => setPay({ ...pay, invoice_id: e.target.value })}>
                  <option value="">Select invoice</option>
                  {invoices.map((i) => (
                    <option key={i.id} value={i.id}>{i.invoice_id} · {money(i.patient_amount)} due · {i.status}</option>
                  ))}
                </select>
              </label>
              <label>Amount<input required type="number" min="0.01" step="0.01" value={pay.amount} onChange={(e) => setPay({ ...pay, amount: e.target.value })} /></label>
              <label>Method
                <select value={pay.payment_method} onChange={(e) => setPay({ ...pay, payment_method: e.target.value })}>
                  <option value="CASH">Cash</option>
                  <option value="MPESA">M-Pesa</option>
                  <option value="CARD">Card</option>
                  <option value="BANK">Bank</option>
                </select>
              </label>
              <div className="full actions"><button type="submit" disabled={busy || !pay.invoice_id}>{busy ? "Posting…" : "Record payment"}</button></div>
            </form>
          </article>
        </>
      )}
    </section>
  );
}
