import { useEffect, useState, type FormEvent } from "react";
import { createNetworkPayer, createNetworkPayerPlan, getNetworkPayerPlans, getNetworkPayers, updateNetworkPayerPlanStatus, updateNetworkPayerStatus, type NetworkPayer, type NetworkPayerPlan } from "../api/payerNetwork";

type PayerStatus = "APPLICATION" | "ACTIVE" | "SUSPENDED" | "INACTIVE";

export function NationalPayerNetworkPage() {
  const [payers, setPayers] = useState<NetworkPayer[]>([]);
  const [selected, setSelected] = useState<NetworkPayer | null>(null);
  const [plans, setPlans] = useState<NetworkPayerPlan[]>([]);
  const [status, setStatus] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [showPlan, setShowPlan] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [code, setCode] = useState("");
  const [planName, setPlanName] = useState("");
  const [planCode, setPlanCode] = useState("");
  const [reason, setReason] = useState("");
  const [nextStatus, setNextStatus] = useState<PayerStatus | "">("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    setLoading(true); setError("");
    try { setPayers(await getNetworkPayers(status || undefined)); }
    catch (err) { setError(err instanceof Error ? err.message : "PAYER_NETWORK_REQUEST_FAILED"); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  async function selectPayer(payer: NetworkPayer) {
    setSelected(payer); setError("");
    try { setPlans(await getNetworkPayerPlans(payer.id)); }
    catch (err) { setError(err instanceof Error ? err.message : "PAYER_PLAN_REQUEST_FAILED"); }
  }

  async function createPayer(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setMessage("");
    try { await createNetworkPayer({ name: name.trim(), payer_type: type.trim(), code: code.trim() }); setName(""); setType(""); setCode(""); setShowCreate(false); setMessage("Payer registered in APPLICATION status."); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "PAYER_NETWORK_REQUEST_FAILED"); }
    finally { setSaving(false); }
  }

  async function createPlan(event: FormEvent) {
    event.preventDefault(); if (!selected) return; setSaving(true); setError("");
    try { const plan = await createNetworkPayerPlan(selected.id, { name: planName.trim(), code: planCode.trim() }); setPlans((items) => [...items, plan]); setPlanName(""); setPlanCode(""); setShowPlan(false); setMessage("Payer plan created."); }
    catch (err) { setError(err instanceof Error ? err.message : "PAYER_PLAN_REQUEST_FAILED"); }
    finally { setSaving(false); }
  }

  async function changeStatus() {
    if (!selected || !nextStatus) return; setSaving(true); setError(""); setMessage("");
    try { const updated = await updateNetworkPayerStatus(selected.id, nextStatus, reason.trim()); setSelected(updated); setNextStatus(""); setReason(""); setMessage(`Payer status changed to ${updated.status}.`); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "PAYER_STATUS_UPDATE_FAILED"); }
    finally { setSaving(false); }
  }

  async function changePlanStatus(plan: NetworkPayerPlan) {
    try { const updated = await updateNetworkPayerPlanStatus(plan.id, plan.status === "ACTIVE" ? "INACTIVE" : "ACTIVE"); setPlans((items) => items.map((item) => item.id === updated.id ? updated : item)); }
    catch (err) { setError(err instanceof Error ? err.message : "PAYER_PLAN_STATUS_UPDATE_FAILED"); }
  }

  return <section className="page-stack">
    <div className="page-header"><div><p className="eyebrow">National administration</p><h1>Payer network</h1><p className="muted">Register and govern payers and their plans before they participate in AfyaSync financing workflows.</p></div><button type="button" onClick={() => setShowCreate((v) => !v)}>{showCreate ? "Close registration" : "Register payer"}</button></div>
    {error && <div className="error-banner">{error === "PERMISSION_DENIED" ? "National payer administration permission required." : error}</div>}
    {message && <div className="success-banner">{message}</div>}
    {showCreate && <form className="card form-grid" onSubmit={createPayer}><div className="card-header"><div><h2>Register payer</h2><p className="muted">New payers enter APPLICATION and must be activated through the controlled lifecycle.</p></div></div><label>Name<input required minLength={2} value={name} onChange={(e) => setName(e.target.value)} /></label><label>Payer type<input required minLength={2} placeholder="National scheme, insurer, employer…" value={type} onChange={(e) => setType(e.target.value)} /></label><label>Code<input required minLength={2} value={code} onChange={(e) => setCode(e.target.value)} /></label><div className="form-actions full-width"><button disabled={saving}>{saving ? "Registering…" : "Register payer"}</button></div></form>}
    <div className="card"><div className="card-header"><div><h2>Payer registry</h2><p className="muted">National payer metadata only. Coverage records remain facility-scoped.</p></div><button className="secondary" type="button" disabled={loading} onClick={() => void load()}>{loading ? "Loading…" : "Refresh"}</button></div><div className="filter-row"><label>Status<select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option><option value="APPLICATION">Application</option><option value="ACTIVE">Active</option><option value="SUSPENDED">Suspended</option><option value="INACTIVE">Inactive</option></select></label><button type="button" className="secondary filter-action" onClick={() => void load()}>Apply filter</button></div>{loading ? <p className="muted">Loading payer network…</p> : payers.length === 0 ? <div className="empty-state"><strong>No payers found</strong><span>Register a payer or adjust the status filter.</span></div> : <div className="table-wrap"><table><thead><tr><th>Payer</th><th>Type</th><th>Status</th><th>Integration</th><th>Actions</th></tr></thead><tbody>{payers.map((payer) => <tr key={payer.id}><td><button type="button" className="table-link" onClick={() => void selectPayer(payer)}><strong>{payer.name}</strong></button><div className="muted small">{payer.code}</div></td><td>{payer.payer_type}</td><td><span className="status-badge">{payer.status}</span></td><td>{payer.integration_status}</td><td>{selected?.id === payer.id ? "Selected" : <button type="button" className="secondary compact" onClick={() => void selectPayer(payer)}>Manage</button>}</td></tr>)}</tbody></table></div>}</div>
    {selected && <div className="card"><div className="card-header"><div><p className="eyebrow">Payer configuration</p><h2>{selected.name}</h2><p className="muted">{selected.code} · {selected.payer_type}</p></div><button type="button" onClick={() => setShowPlan((v) => !v)} disabled={selected.status !== "ACTIVE"}>{showPlan ? "Close plan form" : "Add plan"}</button></div><div className="form-grid"><label>Next lifecycle action<select value={nextStatus} onChange={(e) => setNextStatus(e.target.value as PayerStatus)}><option value="">Select action</option>{selected.status === "APPLICATION" && <><option value="ACTIVE">Approve & activate</option><option value="INACTIVE">Close application</option></>}{selected.status === "ACTIVE" && <><option value="SUSPENDED">Suspend</option><option value="INACTIVE">Inactivate</option></>}{selected.status === "SUSPENDED" && <><option value="ACTIVE">Reinstate</option><option value="INACTIVE">Inactivate</option></>}{selected.status === "INACTIVE" && <option value="APPLICATION">Reopen application</option>}</select></label><label>Reason<textarea rows={2} minLength={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Required for every payer status decision" /></label><div className="form-actions"><button type="button" disabled={!nextStatus || reason.trim().length < 3 || saving} onClick={() => void changeStatus()}>Apply lifecycle decision</button></div></div>{showPlan && <form className="card form-grid" onSubmit={createPlan}><label>Plan name<input required value={planName} onChange={(e) => setPlanName(e.target.value)} /></label><label>Plan code<input required value={planCode} onChange={(e) => setPlanCode(e.target.value)} /></label><div className="form-actions full-width"><button disabled={saving}>{saving ? "Creating…" : "Create plan"}</button></div></form>}<div className="table-wrap"><table><thead><tr><th>Plan</th><th>Code</th><th>Status</th><th>Action</th></tr></thead><tbody>{plans.map((plan) => <tr key={plan.id}><td>{plan.name}</td><td>{plan.code}</td><td><span className="status-badge">{plan.status}</span></td><td><button type="button" className="secondary compact" onClick={() => void changePlanStatus(plan)}>{plan.status === "ACTIVE" ? "Deactivate" : "Activate"}</button></td></tr>)}</tbody></table></div></div>}
  </section>;
}
