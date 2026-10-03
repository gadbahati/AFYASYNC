import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { quoteBenefit, listBenefitRules } from "../api/benefitEngineApi";

export function BenefitEnginePage() {
  const [payerId, setPayerId] = useState("");
  const [planId, setPlanId] = useState("");
  const [packageId, setPackageId] = useState("");
  const [service, setService] = useState("CONSULT-OP");
  const [type, setType] = useState("CONSULTATION");
  const [gross, setGross] = useState("1500");
  const [asOf, setAsOf] = useState("");
  const [rules, setRules] = useState<any[]>([]);
  const [packages, setPackages] = useState<any[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.listBenefitPackages?.().then(setPackages).catch(() => setPackages([]));
  }, []);

  useEffect(() => {
    if (!payerId) {
      setRules([]);
      return;
    }
    void listBenefitRules({ payer_id: payerId, status: "ACTIVE" })
      .then(setRules)
      .catch(() => setRules([]));
  }, [payerId]);

  async function run() {
    setLoading(true);
    setError("");
    try {
      setResult(
        await quoteBenefit({
          payer_id: payerId,
          payer_plan_id: planId || null,
          benefit_package_id: packageId || null,
          service_code: service || null,
          service_type: type || null,
          gross_amount: Number(gross),
          as_of: asOf || null,
        }),
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Phase 103 · Universal financing rules</p>
          <h1>Benefits & tariff engine</h1>
          <p className="muted">
            Versioned rules for tariffs, payer share, patient responsibility and preauthorization.
            Most specific ACTIVE rule wins (service code + plan over type-only fallbacks).
          </p>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <article className="card">
        <h2>Run benefit quote</h2>
        <div className="form-grid">
          <label>
            Payer ID
            <input value={payerId} onChange={(e) => setPayerId(e.target.value)} placeholder="UUID" required />
          </label>
          <label>
            Plan ID (optional)
            <input value={planId} onChange={(e) => setPlanId(e.target.value)} placeholder="UUID" />
          </label>
          <label>
            Benefit package
            <select value={packageId} onChange={(e) => setPackageId(e.target.value)}>
              <option value="">Any / not set</option>
              {packages.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.package_code})
                </option>
              ))}
            </select>
          </label>
          <label>
            Service code
            <input value={service} onChange={(e) => setService(e.target.value)} placeholder="e.g. CONSULT-OP" />
          </label>
          <label>
            Service type
            <input value={type} onChange={(e) => setType(e.target.value)} placeholder="e.g. CONSULTATION" />
          </label>
          <label>
            Gross amount (KES)
            <input type="number" min="0" step="0.01" value={gross} onChange={(e) => setGross(e.target.value)} />
          </label>
          <label>
            As of date
            <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
          </label>
        </div>
        <div className="form-actions">
          <button type="button" disabled={loading || !payerId} onClick={() => void run()}>
            {loading ? "Quoting…" : "Quote benefit"}
          </button>
        </div>
      </article>

      {result && (
        <article className="card">
          <h2>Quote result · {result.decision}</h2>
          <p className="muted small">{result.reason_code}</p>
          <div
            className="stat-grid"
            style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 12 }}
          >
            <div className="stat-card">
              <div className="muted small">Gross</div>
              <div className="stat-value">{result.gross_amount}</div>
            </div>
            <div className="stat-card">
              <div className="muted small">Allowed</div>
              <div className="stat-value">{result.allowed_amount}</div>
            </div>
            <div className="stat-card">
              <div className="muted small">Payer</div>
              <div className="stat-value">{result.payer_amount}</div>
            </div>
            <div className="stat-card">
              <div className="muted small">Patient</div>
              <div className="stat-value">{result.patient_amount}</div>
            </div>
          </div>
          {Array.isArray(result.explanation) && result.explanation.length > 0 && (
            <ul className="muted" style={{ marginTop: 12 }}>
              {result.explanation.map((line: string) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}
          {result.requires_preauth && (
            <p className="error">Preauthorization required before full cover.</p>
          )}
        </article>
      )}

      <article className="card">
        <h2>Active rules for payer ({rules.length})</h2>
        {!payerId && <p className="muted">Enter a payer ID to load rules.</p>}
        {payerId && rules.length === 0 && <p className="muted">No ACTIVE rules for this payer.</p>}
        {rules.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Code</th>
                  <th>Type</th>
                  <th>Tariff</th>
                  <th>Payer %</th>
                  <th>Preauth</th>
                  <th>Version</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r) => (
                  <tr key={r.id}>
                    <td>{r.name}</td>
                    <td>{r.service_code || "—"}</td>
                    <td>{r.service_type || "—"}</td>
                    <td>{r.tariff_amount ?? "—"}</td>
                    <td>{r.payer_percent}</td>
                    <td>{r.requires_preauth ? "Yes" : "No"}</td>
                    <td>{r.version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </section>
  );
}
