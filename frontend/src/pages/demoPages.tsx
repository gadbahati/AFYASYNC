import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { FeatureListPage } from "./FeatureListPage";
import type { Referral } from "../api/types";

export function LabPage() {
  return <FeatureListPage title="Laboratory" subtitle="Orders and results" columns={[{ key: "order", label: "Order" }, { key: "patient", label: "Patient" }, { key: "tests", label: "Tests" }, { key: "priority", label: "Priority" }, { key: "status", label: "Status" }]} rows={[{ order: "LAB-1001", patient: "Amina Wanjiku", tests: "FBC, Malaria", priority: "ROUTINE", status: "ORDERED" }, { order: "LAB-1002", patient: "Brian Ochieng", tests: "RBS", priority: "STAT", status: "IN_PROGRESS" }, { order: "LAB-1003", patient: "Faith Mwangi", tests: "Urinalysis", priority: "ROUTINE", status: "RESULTED" }]} />;
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
