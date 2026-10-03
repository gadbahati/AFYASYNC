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
  const [importJson, setImportJson] = useState(`[\n  {\n    "benefit_package_id": "",\n    "payer_id": "",\n    "name": "OP consultation",\n    "service_code": "CONSULT-OP",\n    "service_type": "CONSULTATION",\n    "tariff_amount": 1500,\n    "payer_percent": 100,\n    "requires_preauth": false,\n    "effective_from": "2026-01-01",\n    "status": "ACTIVE"\n  }\n]`);
  const [importResult, setImportResult] = useState<any>(null);

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

  async function runImport() {
    setLoading(true);
    setError("");
    setImportResult(null);
    try {
      const parsed = JSON.parse(importJson);
      if (!Array.isArray(parsed)) throw new Error("JSON must be an array of rules");
      const res = await api.importBenefitRules({ rules: parsed, stop_on_error: false });
      setImportResult(res);
      if (payerId) {
        const list = await listBenefitRules({ payer_id: payerId, status: "ACTIVE" });
        setRules(list);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

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
          <p className="eyebrow">Phase 114 · Universal financing rules</p>
          <h1>Benefits & tariff engine</h1>
          <p className="muted">
            Versioned rules for tariffs, payer share, patient responsibility and preauthorization. Bulk-import
            national tariff packs as JSON.
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
            Package
            <select value={packageId} onChange={(e) => setPackageId(e.target.value)}>
              <option value="">Any</option>
              {packages.map((p: any) => (
                <option key={p.id} value={p.id}>
                  {p.name || p.id}
                </option>
              ))}
            </select>
          </label>
          <label>
            Service code
            <input value={service} onChange={(e) => setService(e.target.value)} />
          </label>
          <label>
            Service type
            <input value={type} onChange={(e) => setType(e.target.value)} />
          </label>
          <label>
            Gross amount
            <input type="number" min="0" step="0.01" value={gross} onChange={(e) => setGross(e.target.value)} />
          </label>
          <label>
            As of (YYYY-MM-DD)
            <input value={asOf} onChange={(e) => setAsOf(e.target.value)} placeholder="optional" />
          </label>
        </div>
        <div className="form-actions">
          <button type="button" className="primary" disabled={loading || !payerId} onClick={() => void run()}>
            {loading ? "Quoting…" : "Quote"}
          </button>
        </div>
        {result && (
          <pre className="muted small" style={{ marginTop: 12, whiteSpace: "pre-wrap" }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </article>

      <article className="card">
        <h2>ACTIVE rules {payerId ? "for payer" : ""}</h2>
        {!payerId && <p className="muted">Enter a payer ID above to list rules.</p>}
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

      <article className="card">
        <h2>Bulk import tariff rules</h2>
        <p className="muted small">
          Paste a JSON array of benefit rules (max 500). Each rule needs benefit_package_id, payer_id, name,
          effective_from, and service_code or service_type.
        </p>
        <label>
          Rules JSON
          <textarea
            rows={12}
            value={importJson}
            onChange={(e) => setImportJson(e.target.value)}
            style={{ width: "100%", fontFamily: "monospace", fontSize: 12 }}
          />
        </label>
        <div className="form-actions">
          <button type="button" className="primary" disabled={loading} onClick={() => void runImport()}>
            {loading ? "Importing…" : "Import rules"}
          </button>
        </div>
        {importResult && (
          <div className="success-box" style={{ marginTop: 12 }}>
            Created {importResult.created_count} · errors {importResult.error_count}
            {importResult.errors?.length > 0 && (
              <ul className="small">
                {importResult.errors.slice(0, 10).map((e: any, i: number) => (
                  <li key={i}>
                    [{e.index}] {e.error}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        <p className="muted small">Developed by BAHATI GAD WANGWE · Phase 114</p>
      </article>
    </section>
  );
}

export default BenefitEnginePage;
