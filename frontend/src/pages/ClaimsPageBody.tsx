import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { useWorkspace } from "../workspaces/WorkspaceContext";
import { ClaimsClaimsTable } from "./ClaimsClaimsTable";
import { ClaimsKesRiskPanel } from "./ClaimsKesRiskPanel";

type Claim = {
  id: string;
  claim_id: string;
  invoice_id: string;
  payer_id?: string;
  claim_amount: number | string;
  approved_amount: number | string;
  paid_amount: number | string;
  status: string;
};

type RejectionItem = {
  claim_id: string;
  claim_number: string;
  invoice_id: string;
  status: string;
  claim_amount: number;
  response_code: string | null;
  response_message: string | null;
  guide_code: string;
  guide_title: string;
  guide_fix: string;
  guide_owner: string;
};

type RiskFactor = {
  code: string;
  severity: string;
  points: number;
  message: string;
  owner: string;
};

type Preflight = {
  invoice_id: string;
  ready: boolean;
  errors: string[];
  warnings: string[];
  payer_amount: number;
  patient_amount: number;
  item_count: number;
  risk_score?: number;
  risk_band?: string;
  block_submit?: boolean;
  risk_factors?: RiskFactor[];
  benefit_unknown_rules?: number;
  benefit_preauth_lines?: number;
  benefit_ineligible_lines?: number;
  benefit_engine_payer_total?: number;
  benefit_engine_patient_total?: number;
};

type KesAtRisk = {
  kes_at_risk: number;
  kes_rejected: number;
  kes_in_flight: number;
  kes_draft_or_ready: number;
  count_rejected: number;
  count_in_flight: number;
  window_days: number;
};

const money = (n: number | string) =>
  `KES ${Number(n || 0).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const STATUS_FILTERS = [
  "ALL",
  "DRAFT",
  "READY",
  "SUBMITTED",
  "UNDER_REVIEW",
  "ACCEPTED",
  "PARTIALLY_PAID",
  "REJECTED",
  "PAID",
] as const;

const isProd = import.meta.env.PROD;

function canValidate(status: string) {
  return ["DRAFT", "READY", "REJECTED"].includes(status);
}
function canSubmit(status: string) {
  return status === "READY";
}
function canRespond(status: string) {
  return ["SUBMITTED", "UNDER_REVIEW"].includes(status);
}
function canReconcile(status: string) {
  return ["ACCEPTED", "PARTIALLY_PAID", "PAID"].includes(status);
}
function canSandboxReject(status: string) {
  return !isProd && ["READY", "SUBMITTED", "UNDER_REVIEW"].includes(status);
}

export function ClaimsPage() {
  const { scope } = useWorkspace();
  const [claims, setClaims] = useState<Claim[]>([]);
  const [rejections, setRejections] = useState<RejectionItem[]>([]);
  const [invoiceId, setInvoiceId] = useState("");
  const [preflight, setPreflight] = useState<Preflight | null>(null);
  const [kesRisk, setKesRisk] = useState<KesAtRisk | null>(null);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]>("ALL");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [responseClaim, setResponseClaim] = useState<Claim | null>(null);
  const [response, setResponse] = useState({
    status: "ACCEPTED" as "ACCEPTED" | "UNDER_REVIEW" | "REJECTED" | "PARTIALLY_PAID" | "PAID",
    code: "",
    message: "",
    reference: "",
    approved: "",
  });
  const [reconcileClaim, setReconcileClaim] = useState<Claim | null>(null);
  const [receivedAmount, setReceivedAmount] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [c, r, k] = await Promise.all([
        api.listClaims(50, scope),
        api.listClaimRejections(),
        api.claimsKesAtRisk(7).catch(() => null),
      ]);
      setClaims(Array.isArray(c) ? c : []);
      setRejections(Array.isArray(r) ? r : []);
      setKesRisk(k);
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "CLAIMS_LOAD_FAILED");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [scope]);

  const filtered = useMemo(() => {
    if (statusFilter === "ALL") return claims;
    return claims.filter((c) => c.status === statusFilter);
  }, [claims, statusFilter]);

  const stats = useMemo(() => {
    const by = (s: string) => claims.filter((c) => c.status === s).length;
    const totalClaimed = claims.reduce((sum, c) => sum + Number(c.claim_amount || 0), 0);
    const totalPaid = claims.reduce((sum, c) => sum + Number(c.paid_amount || 0), 0);
    return {
      total: claims.length,
      rejected: by("REJECTED"),
      submitted: by("SUBMITTED") + by("UNDER_REVIEW"),
      accepted: by("ACCEPTED") + by("PARTIALLY_PAID"),
      totalClaimed,
      totalPaid,
    };
  }, [claims]);

  async function runPreflight() {
    const id = invoiceId.trim();
    if (!UUID_RE.test(id)) {
      setError("Invoice ID must be a valid UUID.");
      return;
    }
    setBusy(true);
    setError(null);
    setPreflight(null);
    try {
      const result = await api.claimPreflight(id);
      setPreflight(result);
      setMessage(result.ready ? "Preflight passed — invoice is ready for claim creation." : null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "PREFLIGHT_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    const id = invoiceId.trim();
    if (!UUID_RE.test(id)) {
      setError("Invoice ID must be a valid UUID.");
      return;
    }
    if (preflight && (!preflight.ready || preflight.block_submit)) {
      setError("Fix preflight risk factors before creating a claim.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.createClaim(id);
      setInvoiceId("");
      setPreflight(null);
      setMessage("Claim created from the invoice.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "CLAIM_CREATE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function action(fn: () => Promise<unknown>, ok: string) {
    setBusy(true);
    setError(null);
    try {
      const r = (await fn()) as { message?: string; errors?: string[]; valid?: boolean } | undefined;
      if (r && Array.isArray(r.errors) && r.errors.length > 0) {
        setError(r.errors.join("; "));
        setMessage(null);
      } else {
        setMessage(r?.message || ok);
      }
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "CLAIM_ACTION_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onResponse(e: FormEvent) {
    e.preventDefault();
    if (!responseClaim) return;
    const code = response.code.trim();
    const msg = response.message.trim();
    const ref = response.reference.trim();
    if (!code || !msg || !ref) {
      setError("Response code, message, and external reference are required.");
      return;
    }
    const approved = response.status === "REJECTED" ? 0 : Number(response.approved || 0);
    setBusy(true);
    setError(null);
    try {
      await api.recordClaimResponse(responseClaim.id, {
        status: response.status,
        response_code: code,
        response_message: msg,
        external_reference: ref,
        approved_amount: approved,
      });
      setMessage("Payer response recorded.");
      setResponseClaim(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "PAYER_RESPONSE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onReconcile(e: FormEvent) {
    e.preventDefault();
    if (!reconcileClaim) return;
    const amount = Number(receivedAmount);
    if (Number.isNaN(amount) || amount < 0) {
      setError("Received amount must be a non-negative number.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const r = await api.reconcileClaim(reconcileClaim.id, amount);
      setMessage(`Reconciliation ${r.status || "recorded"}.`);
      setReconcileClaim(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "RECONCILIATION_FAILED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Revenue & financing · Phase 116</p>
          <h1>Claims & rework</h1>
          <p className="muted">
            Claims under <strong>{scope}</strong> scope — preflight, validate, submit, response, and reconciliation.
          </p>
        </div>
        <button type="button" className="button secondary" onClick={() => void load()}>
          Refresh
        </button>
      </header>

      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {message && <div className="success-box">{message}</div>}

      <div className="stats-row">
        <div className="stat-card">
          <span className="muted small">Total claims</span>
          <strong>{stats.total}</strong>
        </div>
        <div className="stat-card">
          <span className="muted small">In flight</span>
          <strong>{stats.submitted}</strong>
        </div>
        <div className="stat-card">
          <span className="muted small">Accepted</span>
          <strong>{stats.accepted}</strong>
        </div>
        <div className="stat-card">
          <span className="muted small">Rejected</span>
          <strong>{stats.rejected}</strong>
        </div>
        <div className="stat-card">
          <span className="muted small">Claimed</span>
          <strong>{money(stats.totalClaimed)}</strong>
        </div>
        <div className="stat-card">
          <span className="muted small">Paid</span>
          <strong>{money(stats.totalPaid)}</strong>
        </div>
        {kesRisk && (
          <div className="stat-card">
            <span className="muted small">KES at risk ({kesRisk.window_days}d)</span>
            <strong>{money(kesRisk.kes_at_risk)}</strong>
          </div>
        )}
      </div>

      <ClaimsKesRiskPanel kesRisk={kesRisk} money={money} />

      <article className="card">
        <h2>Create claim from invoice</h2>
        <p className="muted small">
          Run <strong>preflight</strong> first. Risk score shows rejection likelihood before you create the claim.
        </p>
        <form className="form-grid" onSubmit={onCreate}>
          <label className="span-2">
            Invoice ID
            <input
              required
              value={invoiceId}
              onChange={(e) => {
                setInvoiceId(e.target.value);
                setPreflight(null);
              }}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              autoComplete="off"
              spellCheck={false}
            />
          </label>
          <div className="form-actions span-2">
            <button
              type="button"
              className="secondary"
              disabled={busy || !invoiceId.trim()}
              onClick={() => void runPreflight()}
            >
              Run preflight
            </button>
            <button
              type="submit"
              disabled={busy || (preflight != null && (!preflight.ready || !!preflight.block_submit))}
            >
              Create claim
            </button>
          </div>
        </form>
        {preflight && (
          <div className={preflight.ready ? "success-box" : "error"} style={{ marginTop: "1rem" }}>
            <strong>
              {preflight.ready ? "Ready for claim" : "Not ready"}
              {preflight.risk_band != null && (
                <>
                  {" "}· Risk {preflight.risk_band} ({preflight.risk_score ?? 0}/100)
                </>
              )}
            </strong>
            <p className="small" style={{ margin: "0.35rem 0 0" }}>
              Items: {preflight.item_count} · Payer: {money(preflight.payer_amount)} · Patient:{" "}
              {money(preflight.patient_amount)}
              {preflight.block_submit ? " · Submit blocked until fixes applied" : ""}
            </p>
            {(preflight.benefit_engine_payer_total != null ||
              preflight.benefit_preauth_lines != null ||
              preflight.benefit_unknown_rules != null) && (
              <p className="small muted" style={{ margin: "0.35rem 0 0" }}>
                Benefit engine · payer {money(preflight.benefit_engine_payer_total ?? 0)} · patient{" "}
                {money(preflight.benefit_engine_patient_total ?? 0)}
                {preflight.benefit_preauth_lines
                  ? ` · preauth lines ${preflight.benefit_preauth_lines}`
                  : ""}
                {preflight.benefit_unknown_rules
                  ? ` · missing rules ${preflight.benefit_unknown_rules}`
                  : ""}
                {preflight.benefit_ineligible_lines
                  ? ` · excluded ${preflight.benefit_ineligible_lines}`
                  : ""}
              </p>
            )}
            {preflight.errors?.length > 0 && (
              <ul className="small" style={{ marginTop: "0.5rem" }}>
                {preflight.errors.map((err) => (
                  <li key={err}>{err}</li>
                ))}
              </ul>
            )}
            {preflight.warnings?.length > 0 && (
              <ul className="small muted" style={{ marginTop: "0.35rem" }}>
                {preflight.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </article>

      <ClaimsClaimsTable
        loading={loading}
        scope={scope}
        filtered={filtered}
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        statusFilters={STATUS_FILTERS}
        busy={busy}
        action={action}
        canValidate={canValidate}
        canSubmit={canSubmit}
        canRespond={canRespond}
        canReconcile={canReconcile}
        canSandboxReject={canSandboxReject}
        setResponseClaim={setResponseClaim}
        setResponse={setResponse}
        setReconcileClaim={setReconcileClaim}
        setReceivedAmount={setReceivedAmount}
        responseClaim={responseClaim}
        response={response}
        onResponse={onResponse}
        reconcileClaim={reconcileClaim}
        receivedAmount={receivedAmount}
        onReconcile={onReconcile}
        rejections={rejections}
        money={money}
        stats={stats}
        kesRisk={kesRisk}
      />
    </section>
  );
}
