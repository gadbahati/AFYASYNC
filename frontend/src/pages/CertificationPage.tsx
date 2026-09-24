import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

type Kit = {
  title?: string;
  phase?: number;
  checklist_summary?: { domains?: number; controls_total?: number; controls_implemented?: number; completion_ratio?: number };
  domains?: Array<{ domain: string; title: string; implemented: number; total: number; pct: number }>;
  evidence_index?: Array<{ ref: string; path: string }>;
  operator_actions?: Array<{ id: string; action: string; owner: string; blocks_cert: boolean; blocks_live_claims: boolean }>;
  readiness?: { software_controls_ready?: boolean; security_posture_high_severity_ok?: boolean; external_pen_test?: boolean; dha_portal_submission?: boolean; live_sha_credentials?: boolean };
  submission_notes?: string[];
  disclaimer?: string;
  generated_at?: string;
};

function bool(v: boolean | undefined) { return v ? "Ready" : "Open"; }

export function CertificationPage() {
  const [kit, setKit] = useState<Kit | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setKit(await api.certificationSubmissionKit() as Kit); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to load certification kit"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const summary = kit?.checklist_summary;
  const readiness = kit?.readiness;
  return <section>
    <div className="page-header">
      <div><div className="eyebrow">PHASE 30 • CERTIFICATION READINESS</div><h1>DHA submission kit</h1><p className="muted">Auditor-facing evidence index and operational actions for DHA review.</p></div>
      <button className="button secondary" type="button" onClick={() => void load()} disabled={loading}>{loading ? "Refreshing…" : "Refresh"}</button>
    </div>
    {error && <div className="alert error">{error}</div>}
    {loading && !kit ? <div className="card"><p>Loading submission evidence…</p></div> : kit && <>
      <div className="grid grid-4">
        <div className="card stat"><span>Controls</span><strong>{summary?.controls_total ?? 0}</strong><small>{summary?.controls_implemented ?? 0} implemented</small></div>
        <div className="card stat"><span>Completion</span><strong>{Math.round((summary?.completion_ratio ?? 0) * 100)}%</strong><small>{summary?.domains ?? 0} evidence domains</small></div>
        <div className="card stat"><span>Software controls</span><strong>{bool(readiness?.software_controls_ready)}</strong><small>Implementation gate</small></div>
        <div className="card stat"><span>Security gate</span><strong>{bool(readiness?.security_posture_high_severity_ok)}</strong><small>Critical/high checks</small></div>
      </div>

      <div className="grid grid-2">
        <div className="card"><div className="card-header"><div><h2>Readiness gates</h2><p className="muted">Current state returned by the certification backend.</p></div></div>
          <div className="table-wrap"><table><thead><tr><th>Gate</th><th>Status</th></tr></thead><tbody>
            <tr><td>Software controls</td><td><span className="badge">{bool(readiness?.software_controls_ready)}</span></td></tr>
            <tr><td>Critical/high security checks</td><td><span className="badge">{bool(readiness?.security_posture_high_severity_ok)}</span></td></tr>
            <tr><td>Independent penetration test</td><td><span className="badge">{bool(readiness?.external_pen_test)}</span></td></tr>
            <tr><td>DHA portal submission</td><td><span className="badge">{bool(readiness?.dha_portal_submission)}</span></td></tr>
            <tr><td>Live SHA credentials</td><td><span className="badge">{bool(readiness?.live_sha_credentials)}</span></td></tr>
          </tbody></table></div>
        </div>
        <div className="card"><div className="card-header"><div><h2>Evidence domains</h2><p className="muted">Control coverage by certification domain.</p></div></div>
          <div className="stack">{(kit.domains || []).map(d => <div className="list-row" key={d.domain}><div><strong>{d.title}</strong><span className="muted small">{d.domain} • {d.implemented}/{d.total} controls</span></div><strong>{d.pct}%</strong></div>)}</div>
        </div>
      </div>

      <div className="card"><div className="card-header"><div><h2>Operator actions</h2><p className="muted">Items that remain outside the software implementation itself.</p></div></div>
        <div className="table-wrap"><table><thead><tr><th>ID</th><th>Action</th><th>Owner</th><th>Certification</th><th>Live claims</th></tr></thead><tbody>
          {(kit.operator_actions || []).map(a => <tr key={a.id}><td>{a.id}</td><td>{a.action}</td><td>{a.owner}</td><td>{a.blocks_cert ? "Blocks" : "Does not block"}</td><td>{a.blocks_live_claims ? "Blocks" : "Does not block"}</td></tr>)}
        </tbody></table></div>
      </div>

      <div className="grid grid-2">
        <div className="card"><div className="card-header"><div><h2>Evidence index</h2><p className="muted">Live AfyaSync endpoints referenced by the kit.</p></div></div>
          <div className="stack">{(kit.evidence_index || []).map(e => <div className="list-row" key={e.ref}><strong>{e.ref}</strong><code>{e.path}</code></div>)}</div>
        </div>
        <div className="card"><div className="card-header"><div><h2>Submission notes</h2><p className="muted">Assembly guidance returned by the backend.</p></div></div>
          <ul>{(kit.submission_notes || []).map(n => <li key={n}>{n}</li>)}</ul>
          <div className="notice"><strong>Important:</strong> {kit.disclaimer || "This is an evidence-organising tool, not an official certificate."}</div>
        </div>
      </div>
      <p className="muted small">Generated {kit.generated_at ? new Date(kit.generated_at).toLocaleString() : "—"}.</p>
    </>}
  </section>;
}
