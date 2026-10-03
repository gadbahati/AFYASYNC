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
  const [rules, setRules] = useState<any[]>([]);
  const [packages, setPackages] = useState<any[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [importText, setImportText] = useState(
    "benefit_package_id,payer_id,name,service_code,service_type,tariff_amount,payer_percent,requires_preauth,effective_from,status\n,,OP consultation,CONSULT-OP,CONSULTATION,1500,100,false,2026-01-01,ACTIVE",
  );
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

  function parseCsvRules(text: string): any[] {
    const lines = text.trim().split(/\r?\n/).filter(Boolean);
    if (lines.length < 2) throw new Error("CSV needs header + at least one row");
    const headers = lines[0].split(",").map((h) => h.trim());
    return lines.slice(1).map((line) => {
      const cols = line.split(",").map((c) => c.trim());
      const row: any = {};
      headers.forEach((h, i) => {
        const v = cols[i] ?? "";
        if (
          ["tariff_amount", "payer_percent", "fixed_patient_copay", "max_covered_amount", "version"].includes(h)
        ) {
          row[h] = v === "" ? null : Number(v);
        } else if (["requires_preauth", "is_excluded"].includes(h)) {
          row[h] = v.toLowerCase() === "true" || v === "1" || v.toLowerCase() === "yes";
        } else if (v !== "") {
          row[h] = v;
        }
      });
      return row;
    });
  }

  async function runImport(mode: "json" | "csv") {
    setLoading(true);
    setError("");
    setImportResult(null);
    try {
      let rulesPayload: any[];
      if (mode === "csv") {
        rulesPayload = parseCsvRules(importText);
      } else {
        const parsed = JSON.parse(importText);
        if (!Array.isArray(parsed)) throw new Error("JSON must be an array of rules");
        rulesPayload = parsed;
      }
      const res = await api.importBenefitRules({ rules: rulesPayload, stop_on_error: false });
      setImportResult(res);
      if (payerId) {
        setRules(await listBenefitRules({ payer_id: payerId, status: "ACTIVE" }));
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
          as_of: null,
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
          <p className="eyebrow">Phase 115 · Tariff import</p>
          <h1>Benefits & tariff engine</h1>
          <p className="muted">Quote rules, list ACTIVE tariffs, and bulk-import via JSON or CSV.</p>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <article className="card">
        <h2>Run benefit quote</h2>
        <div className="form-grid">
          <label>
            Payer ID
            <input value={payerId} onChange={(e) => setPayerId(e.target.value)} placeholder="UUID" />
          </label>
          <label>
            Plan ID
            <input value={planId} onChange={(e) => setPlanId(e.target.value)} />
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
            Gross
            <input type="number" value={gross} onChange={(e) => setGross(e.target.value)} />
          </label>
        </div>
        <div className="form-actions">
          <button type="button" className="primary" disabled={loading || !payerId} onClick={() => void run()}>
            Quote
          </button>
        </div>
        {result && (
          <pre className="muted small" style={{ whiteSpace: "pre-wrap" }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </article>

      <article className="card">
        <h2>ACTIVE rules</h2>
        {!payerId && <p className="muted">Enter payer ID to list rules.</p>}
        {payerId && rules.length === 0 && <p className="muted">No ACTIVE rules.</p>}
        {rules.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Code</th>
                  <th>Tariff</th>
                  <th>Payer %</th>
                  <th>Preauth</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r) => (
                  <tr key={r.id}>
                    <td>{r.name}</td>
                    <td>{r.service_code || "—"}</td>
                    <td>{r.tariff_amount ?? "—"}</td>
                    <td>{r.payer_percent}</td>
                    <td>{r.requires_preauth ? "Yes" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>

      <article className="card">
        <h2>Bulk import (JSON or CSV)</h2>
        <p className="muted small">
          CSV needs a header row. Required: benefit_package_id, payer_id, name, effective_from, and service_code or
          service_type.
        </p>
        <textarea
          rows={10}
          value={importText}
          onChange={(e) => setImportText(e.target.value)}
          style={{ width: "100%", fontFamily: "monospace", fontSize: 12 }}
        />
        <div className="form-actions">
          <button type="button" className="primary" disabled={loading} onClick={() => void runImport("json")}>
            Import JSON
          </button>
          <button type="button" className="secondary" disabled={loading} onClick={() => void runImport("csv")}>
            Import CSV
          </button>
        </div>
        {importResult && (
          <div className="success-box" style={{ marginTop: 12 }}>
            Created {importResult.created_count} · errors {importResult.error_count}
          </div>
        )}
        <p className="muted small">Developed by BAHATI GAD WANGWE · Phase 115</p>
      </article>
    </section>
  );
}

export default BenefitEnginePage;
