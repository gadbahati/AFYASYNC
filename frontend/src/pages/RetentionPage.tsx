import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api/client";

type Policy = { class?: string; retention?: string; archive?: string; erasure?: string };
type RequestItem = {
  id: string;
  person_id: string;
  facility_id?: string | null;
  request_type: string;
  status: string;
  reason?: string | null;
  decision_notes?: string | null;
  created_at?: string | null;
  fulfilled_at?: string | null;
};

const statusOptions = ["RECEIVED", "UNDER_REVIEW", "FULFILLED", "REJECTED", "CANCELLED"];

export function RetentionPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [requests, setRequests] = useState<RequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [personId, setPersonId] = useState("");
  const [requestType, setRequestType] = useState("ERASURE");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState("");
  const [selected, setSelected] = useState<RequestItem | null>(null);
  const [decisionStatus, setDecisionStatus] = useState("UNDER_REVIEW");
  const [decisionNotes, setDecisionNotes] = useState("");
  const [applyPseudonym, setApplyPseudonym] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [catalogue, list] = await Promise.all([
        api.retentionPolicies(),
        api.retentionRequests(statusFilter, 100),
      ]);
      setPolicies(catalogue?.policies || []);
      setRequests(list?.requests || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load retention operations.");
    } finally { setLoading(false); }
  }, [statusFilter]);

  useEffect(() => { void load(); }, [load]);

  const submitRequest = async (event: FormEvent) => {
    event.preventDefault();
    if (!personId.trim()) return;
    setBusy("create");
    try {
      await api.createRetentionRequest({ person_id: personId.trim(), request_type: requestType, reason: reason.trim() || null });
      setPersonId(""); setReason("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to create request.");
    } finally { setBusy(""); }
  };

  const decide = async (event: FormEvent) => {
    event.preventDefault();
    if (!selected) return;
    if (decisionStatus === "FULFILLED" && applyPseudonym) {
      const ok = window.confirm("This will pseudonymise direct patient identifiers while retaining the patient row for referential integrity. Continue?");
      if (!ok) return;
    }
    setBusy("decide");
    try {
      await api.decideRetentionRequest(selected.id, {
        status: decisionStatus,
        decision_notes: decisionNotes.trim() || null,
        apply_pseudonym: applyPseudonym,
      });
      setSelected(null); setDecisionNotes(""); setApplyPseudonym(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to decide request.");
    } finally { setBusy(""); }
  };

  return <section className="page">
    <div className="page-header">
      <div><span className="eyebrow">PHASE 33</span><h1>Data retention & erasure</h1><p>Operational controls for retention policy, access/export requests, restrictions and privacy erasure workflows.</p></div>
      <button type="button" className="secondary" onClick={() => void load()} disabled={loading}>Refresh</button>
    </div>

    {error && <div className="notice error">{error}</div>}
    <div className="stats-grid">
      <div className="stat-card"><span>Policies</span><strong>{policies.length}</strong><small>Configured retention classes</small></div>
      <div className="stat-card"><span>Requests</span><strong>{requests.length}</strong><small>Current facility queue</small></div>
      <div className="stat-card"><span>Open</span><strong>{requests.filter(r => !["FULFILLED","REJECTED","CANCELLED"].includes(r.status)).length}</strong><small>Awaiting closure</small></div>
      <div className="stat-card"><span>Erasure</span><strong>{requests.filter(r => r.request_type === "ERASURE").length}</strong><small>Requests in current view</small></div>
    </div>

    <div className="grid-2">
      <div className="card">
        <div className="card-header"><div><h2>Retention policy catalogue</h2><p>Retention periods are operational policy settings and may be longer where law or legal hold requires.</p></div></div>
        <div className="table-wrap"><table><thead><tr><th>Class</th><th>Retention</th><th>Archive</th><th>Erasure handling</th></tr></thead><tbody>
          {policies.map((p, i) => <tr key={p.class || i}><td><strong>{p.class}</strong></td><td>{p.retention}</td><td>{p.archive}</td><td>{p.erasure}</td></tr>)}
        </tbody></table></div>
      </div>
      <div className="card">
        <div className="card-header"><div><h2>New privacy request</h2><p>Use a person ID from the authorised facility workflow. Requests are audited.</p></div></div>
        <form onSubmit={submitRequest} className="form-grid">
          <label>Person ID<input value={personId} onChange={e => setPersonId(e.target.value)} placeholder="UUID" required /></label>
          <label>Request type<select value={requestType} onChange={e => setRequestType(e.target.value)}><option>ERASURE</option><option>RESTRICTION</option><option>ACCESS_EXPORT</option></select></label>
          <label className="full">Reason<textarea value={reason} onChange={e => setReason(e.target.value)} maxLength={2000} rows={4} placeholder="Reason or request context" /></label>
          <div className="full"><button type="submit" disabled={busy === "create" || !personId.trim()}>{busy === "create" ? "Submitting…" : "Submit request"}</button></div>
        </form>
      </div>
    </div>

    <div className="card">
      <div className="card-header"><div><h2>Privacy request queue</h2><p>Facility-scoped requests and their audited decision state.</p></div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}><option value="">All statuses</option>{statusOptions.map(s => <option key={s}>{s}</option>)}</select>
      </div>
      <div className="table-wrap"><table><thead><tr><th>Request</th><th>Person</th><th>Type</th><th>Status</th><th>Created</th><th>Action</th></tr></thead><tbody>
        {requests.map(r => <tr key={r.id}><td><code>{r.id.slice(0, 8)}…</code></td><td><code>{r.person_id.slice(0, 8)}…</code></td><td>{r.request_type}</td><td><span className="badge">{r.status}</span></td><td>{r.created_at ? new Date(r.created_at).toLocaleString() : "—"}</td><td><button type="button" className="secondary" onClick={() => { setSelected(r); setDecisionStatus(r.status === "RECEIVED" ? "UNDER_REVIEW" : r.status); setDecisionNotes(r.decision_notes || ""); setApplyPseudonym(false); }}>Review</button></td></tr>)}
        {!loading && requests.length === 0 && <tr><td colSpan={6}>No privacy requests in this view.</td></tr>}
      </tbody></table></div>
    </div>

    {selected && <div className="modal-backdrop" role="dialog" aria-modal="true"><div className="modal card">
      <div className="card-header"><div><span className="eyebrow">REQUEST REVIEW</span><h2>{selected.request_type}</h2><p>Request <code>{selected.id}</code> for person <code>{selected.person_id}</code></p></div><button type="button" className="secondary" onClick={() => setSelected(null)}>Close</button></div>
      <form onSubmit={decide} className="form-grid">
        <label>Status<select value={decisionStatus} onChange={e => setDecisionStatus(e.target.value)}>{statusOptions.map(s => <option key={s}>{s}</option>)}</select></label>
        <label className="full">Decision notes<textarea value={decisionNotes} onChange={e => setDecisionNotes(e.target.value)} maxLength={2000} rows={4} /></label>
        {selected.request_type === "ERASURE" && decisionStatus === "FULFILLED" && <label className="full checkbox"><input type="checkbox" checked={applyPseudonym} onChange={e => setApplyPseudonym(e.target.checked)} /> Apply pseudonymisation of direct identifiers. This does not delete retained clinical/financial/audit records.</label>}
        <div className="full"><button type="submit" disabled={busy === "decide"}>{busy === "decide" ? "Saving…" : "Save decision"}</button></div>
      </form>
    </div></div>}

    <div className="notice"><strong>Privacy safeguard:</strong> Erasure is not treated as wholesale deletion. Where an erasure request is fulfilled with pseudonymisation, direct identifiers are restricted while records required for clinical continuity, financial audit or legal retention remain intact. Authorised users should follow applicable Kenyan law, legal holds and organisational policy.</div>
  </section>;
}
