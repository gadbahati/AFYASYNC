import { useCallback, useEffect, useState } from "react";
import { getIntegrations, getIntegrationTransactions, updateIntegrationStatus, type Integration, type IntegrationTransaction } from "../api/integrations";

export function IntegrationOperationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [transactions, setTransactions] = useState<IntegrationTransaction[]>([]);
  const [status, setStatus] = useState("ALL");
  const [transactionStatus, setTransactionStatus] = useState("ALL");
  const [integrationId, setIntegrationId] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [selectedAction, setSelectedAction] = useState<{ integration: Integration; status: "ACTIVE" | "SUSPENDED" | "INACTIVE" } | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [nextIntegrations, nextTransactions] = await Promise.all([
        getIntegrations(status === "ALL" ? undefined : status),
        getIntegrationTransactions({
          status: transactionStatus === "ALL" ? undefined : transactionStatus,
          integrationId: integrationId === "ALL" ? undefined : integrationId,
        }),
      ]);
      setIntegrations(nextIntegrations); setTransactions(nextTransactions);
    } catch (err) { setError(err instanceof Error ? err.message : "INTEGRATION_REQUEST_FAILED"); }
    finally { setLoading(false); }
  }, [status, transactionStatus, integrationId]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function applyStatus() {
    if (!selectedAction || reason.trim().length < 3) return;
    try {
      await updateIntegrationStatus(selectedAction.integration.id, selectedAction.status, reason.trim());
      setNotice("Integration status updated."); setSelectedAction(null); setReason(""); await refresh();
    } catch (err) { setError(err instanceof Error ? err.message : "INTEGRATION_STATUS_UPDATE_FAILED"); }
  }

  return <div className="page-stack">
    <div className="page-heading"><div><p className="eyebrow">INTEROPERABILITY</p><h1>Integration operations</h1><p className="muted">Monitor facility payer connections and outbound transaction delivery without exposing integration secrets.</p></div><button className="button secondary" onClick={() => void refresh()} disabled={loading}>Refresh</button></div>
    {error && <div className="error-banner">{error}</div>}
    {notice && <div className="success-banner">{notice}</div>}

    <section className="card"><div className="section-heading"><div><h2>Integration connections</h2><p className="muted">Only integrations belonging to the active facility are shown.</p></div><select value={status} onChange={e => setStatus(e.target.value)}><option>ALL</option><option>ACTIVE</option><option>SUSPENDED</option><option>INACTIVE</option></select></div>
      {loading && integrations.length === 0 ? <p className="muted">Loading integrations…</p> : integrations.length === 0 ? <div className="empty-state"><strong>No integrations configured</strong><span>Connect an authorised payer adapter before attempting live submissions.</span></div> : <div className="table-wrap"><table><thead><tr><th>Name</th><th>Provider</th><th>Type</th><th>Status</th><th>Control</th></tr></thead><tbody>{integrations.map(item => <tr key={item.id}><td>{item.name}</td><td>{item.provider}</td><td>{item.integration_type}</td><td><span className="status-pill">{item.status}</span></td><td><select value="" onChange={e => { const value = e.target.value as "ACTIVE" | "SUSPENDED" | "INACTIVE"; if (value) setSelectedAction({ integration: item, status: value }); }}><option value="">Change status…</option>{item.status !== "ACTIVE" && <option value="ACTIVE">Activate</option>}{item.status !== "SUSPENDED" && <option value="SUSPENDED">Suspend</option>}{item.status !== "INACTIVE" && <option value="INACTIVE">Inactivate</option>}</select></td></tr>)}</tbody></table></div>}
    </section>

    <section className="card"><div className="section-heading"><div><h2>Transaction delivery</h2><p className="muted">Operational state only; payer response details remain behind the claim, payment, or preauthorization workflows.</p></div><div className="toolbar"><select value={transactionStatus} onChange={e => setTransactionStatus(e.target.value)}><option>ALL</option><option>PENDING</option><option>PROCESSING</option><option>RETRYING</option><option>SUCCEEDED</option><option>FAILED</option></select><select value={integrationId} onChange={e => setIntegrationId(e.target.value)}><option value="ALL">All integrations</option>{integrations.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div></div>
      {loading && transactions.length === 0 ? <p className="muted">Loading transactions…</p> : transactions.length === 0 ? <div className="empty-state"><strong>No integration transactions</strong><span>Transactions will appear here when a payer, payment, or preauthorization submission is queued.</span></div> : <div className="table-wrap"><table><thead><tr><th>Transaction</th><th>Entity</th><th>Direction</th><th>Status</th><th>Attempts</th><th>Last attempt</th><th>Response</th></tr></thead><tbody>{transactions.map(item => <tr key={item.id}><td><code>{item.transaction_id}</code></td><td>{item.entity_type}</td><td>{item.direction}</td><td><span className="status-pill">{item.status}</span></td><td>{item.attempt_count}</td><td>{item.last_attempt_at ? new Date(item.last_attempt_at).toLocaleString() : "—"}</td><td>{item.response_code ?? "—"}</td></tr>)}</tbody></table></div>}
    </section>

    {selectedAction && <div className="modal-backdrop" role="presentation"><div className="modal-card"><div className="section-heading"><div><h2>Confirm integration status</h2><p className="muted">This decision is recorded in the facility audit trail.</p></div><button className="button secondary" onClick={() => setSelectedAction(null)}>Cancel</button></div><p><strong>{selectedAction.integration.name}</strong> → {selectedAction.status}</p><label>Reason<textarea value={reason} onChange={e => setReason(e.target.value)} minLength={3} maxLength={500} rows={4} placeholder="Enter an auditable operational reason" /></label><div className="form-actions"><button className="button primary" onClick={() => void applyStatus()} disabled={reason.trim().length < 3}>Confirm</button></div></div></div>}
  </div>;
}
