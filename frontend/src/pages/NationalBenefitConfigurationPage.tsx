import { FormEvent, useEffect, useState } from "react";
import { createNetworkBenefitRule, getNetworkBenefitRules, NetworkBenefitRule, updateNetworkBenefitRuleStatus } from "../api/benefitNetwork";
import { getNetworkPayers, getNetworkPayerPlans, NetworkPayer, NetworkPayerPlan } from "../api/payerNetwork";

export function NationalBenefitConfigurationPage() {
  const [payers, setPayers] = useState<NetworkPayer[]>([]);
  const [plans, setPlans] = useState<NetworkPayerPlan[]>([]);
  const [rules, setRules] = useState<NetworkBenefitRule[]>([]);
  const [payerId, setPayerId] = useState("");
  const [planId, setPlanId] = useState("");
  const [serviceCode, setServiceCode] = useState("");
  const [serviceType, setServiceType] = useState("");
  const [payerPercent, setPayerPercent] = useState("100");
  const [copay, setCopay] = useState("0");
  const [maxCovered, setMaxCovered] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [effectiveTo, setEffectiveTo] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadPayers() {
    const data = await getNetworkPayers("ACTIVE");
    setPayers(data);
    if (!payerId && data.length) setPayerId(data[0].id);
  }
  async function loadPlans(id: string) {
    if (!id) { setPlans([]); setPlanId(""); return; }
    const data = await getNetworkPayerPlans(id);
    const active = data.filter((plan) => plan.status === "ACTIVE");
    setPlans(active);
    if (planId && !active.some((plan) => plan.id === planId)) setPlanId("");
  }
  async function loadRules() {
    setRules(await getNetworkBenefitRules({ payerId: payerId || undefined, payerPlanId: planId || undefined, status: statusFilter || undefined }));
  }
  async function refresh() {
    setLoading(true); setError("");
    try { await loadPayers(); await loadRules(); } catch (err) { setError(err instanceof Error ? err.message : "Unable to load benefit configuration."); } finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);
  useEffect(() => { if (payerId) void loadPlans(payerId).catch((err) => setError(err instanceof Error ? err.message : "Unable to load plans.")); }, [payerId]);
  useEffect(() => { if (!loading) void loadRules().catch((err) => setError(err instanceof Error ? err.message : "Unable to load benefit rules.")); }, [planId, statusFilter]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setMessage("");
    if (!payerId) { setError("Select an active payer."); return; }
    if (!serviceCode.trim() && !serviceType.trim()) { setError("Provide a service code or service type."); return; }
    try {
      await createNetworkBenefitRule({ payer_id: payerId, payer_plan_id: planId || null, service_code: serviceCode.trim() || null, service_type: serviceType.trim() || null, payer_percent: Number(payerPercent), fixed_patient_copay: Number(copay), max_covered_amount: maxCovered ? Number(maxCovered) : null, effective_from: effectiveFrom || null, effective_to: effectiveTo || null });
      setMessage("Benefit rule created."); setServiceCode(""); setServiceType(""); setMaxCovered(""); setEffectiveFrom(""); setEffectiveTo(""); await loadRules();
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to create benefit rule."); }
  }
  async function changeStatus(rule: NetworkBenefitRule) {
    const next = rule.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
    const reason = window.prompt(`Reason for changing this rule to ${next}:`);
    if (!reason?.trim()) return;
    try { await updateNetworkBenefitRuleStatus(rule.id, next, reason.trim()); await loadRules(); setMessage("Benefit rule status updated."); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to update benefit rule."); }
  }
  const payerName = (id: string) => payers.find((payer) => payer.id === id)?.code ?? id.slice(0, 8);
  const planName = (id: string | null) => id ? plans.find((plan) => plan.id === id)?.code ?? id.slice(0, 8) : "All plans";

  return <div className="page-stack">
    <div className="page-header"><div><span className="eyebrow">National financing</span><h1>Benefit configuration</h1><p className="muted">Define real payer and plan rules used by AfyaSync responsibility calculations.</p></div><button type="button" className="secondary" onClick={() => void refresh()} disabled={loading}>Refresh</button></div>
    {error && <div className="error-banner">{error === "PERMISSION_DENIED" ? "National benefit configuration permission required." : error}</div>}{message && <div className="success-banner">{message}</div>}
    <section className="card"><div className="section-heading"><div><h2>Create benefit rule</h2><p className="muted">Rules require an active payer and, when supplied, an active plan belonging to that payer.</p></div></div>
      <form className="form-grid" onSubmit={submit}>
        <label>Payer<select value={payerId} onChange={(e) => setPayerId(e.target.value)} required><option value="">Select payer</option>{payers.map((payer) => <option key={payer.id} value={payer.id}>{payer.code} — {payer.name}</option>)}</select></label>
        <label>Plan<select value={planId} onChange={(e) => setPlanId(e.target.value)}><option value="">All plans</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.code} — {plan.name}</option>)}</select></label>
        <label>Service code<input value={serviceCode} onChange={(e) => setServiceCode(e.target.value)} placeholder="e.g. LAB-CBC" /></label><label>Service type<input value={serviceType} onChange={(e) => setServiceType(e.target.value)} placeholder="e.g. LABORATORY" /></label>
        <label>Payer coverage %<input type="number" min="0" max="100" step="0.01" value={payerPercent} onChange={(e) => setPayerPercent(e.target.value)} required /></label><label>Patient copay<input type="number" min="0" step="0.01" value={copay} onChange={(e) => setCopay(e.target.value)} required /></label>
        <label>Maximum covered amount<input type="number" min="0" step="0.01" value={maxCovered} onChange={(e) => setMaxCovered(e.target.value)} placeholder="Optional" /></label><label>Effective from<input type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} /></label><label>Effective to<input type="date" value={effectiveTo} onChange={(e) => setEffectiveTo(e.target.value)} /></label>
        <div className="form-actions"><button type="submit" disabled={!payerId}>Create rule</button></div>
      </form>
    </section>
    <section className="card"><div className="section-heading"><div><h2>Configured rules</h2><p className="muted">Only persisted payer benefit rules appear here.</p></div><select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="">All statuses</option><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select></div>
      {loading ? <div className="empty-state">Loading benefit configuration…</div> : rules.length === 0 ? <div className="empty-state">No benefit rules match the current filters.</div> : <div className="table-wrap"><table><thead><tr><th>Payer</th><th>Plan</th><th>Scope</th><th>Payer %</th><th>Copay</th><th>Maximum</th><th>Effective</th><th>Status</th><th /></tr></thead><tbody>{rules.map((rule) => <tr key={rule.id}><td>{payerName(rule.payer_id)}</td><td>{planName(rule.payer_plan_id)}</td><td>{rule.service_code || rule.service_type}</td><td>{rule.payer_percent}%</td><td>{rule.fixed_patient_copay}</td><td>{rule.max_covered_amount ?? "—"}</td><td>{rule.effective_from || "Any"}{rule.effective_to ? ` → ${rule.effective_to}` : ""}</td><td><span className={`status-badge status-${rule.status.toLowerCase()}`}>{rule.status}</span></td><td><button type="button" className="linkish" onClick={() => void changeStatus(rule)}>{rule.status === "ACTIVE" ? "Deactivate" : "Activate"}</button></td></tr>)}</tbody></table></div>}
    </section>
  </div>;
}
