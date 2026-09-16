import { useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";

type SimLine = { code: string; description: string; quantity: number; unit_price: number };
type SimResult = {
  coverage_mode: string;
  eligibility: string;
  eligibility_detail: string;
  gross_total: number;
  payer_total: number;
  patient_total: number;
  claimable: boolean;
  warnings: string[];
  lines: Array<{ code: string; description: string; quantity: number; unit_price: number; line_total: number; payer_share: number; patient_share: number; note: string }>;
  guidance: string;
};

const money = (n: number) => `KES ${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function CoverageSimulatorPage() {
  const [mode, setMode] = useState("SHA");
  const [membership, setMembership] = useState("");
  const [lines, setLines] = useState<SimLine[]>([
    { code: "CONSULT", description: "Doctor consultation", quantity: 1, unit_price: 850 },
    { code: "FBC", description: "Full blood count", quantity: 1, unit_price: 500 },
  ]);
  const [result, setResult] = useState<SimResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSimulate(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.simulateCoverage({
        coverage_mode: mode,
        membership_number: membership.trim() || null,
        lines,
      });
      setResult(res as SimResult);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "SIMULATE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Before care · cost certainty</p>
          <h1>Coverage simulator</h1>
          <p className="muted">
            Ask before ordering: under CASH, AFYASYNC or SHA, who pays what? SHA does not give clinicians this clarity inside the care workflow.
          </p>
        </div>
      </header>
      {error && <div className="error">{error}</div>}
      <article className="card">
        <form className="form-grid" onSubmit={onSimulate}>
          <label>Coverage mode
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="CASH">Cash / self-pay</option>
              <option value="AFYASYNC">AfyaSync membership</option>
              <option value="SHA">SHA</option>
              <option value="OTHER">Other payer</option>
            </select>
          </label>
          <label>SHA membership (optional)
            <input value={membership} onChange={(e) => setMembership(e.target.value)} placeholder="e.g. SHA membership number" />
          </label>
          <div className="full">
            <h3>Proposed services</h3>
            {lines.map((line, idx) => (
              <div className="billing-line" key={idx}>
                <label>Code<input value={line.code} onChange={(e) => setLines((c) => c.map((x, i) => i === idx ? { ...x, code: e.target.value } : x))} /></label>
                <label>Description<input value={line.description} onChange={(e) => setLines((c) => c.map((x, i) => i === idx ? { ...x, description: e.target.value } : x))} /></label>
                <label>Qty<input type="number" min={1} value={line.quantity} onChange={(e) => setLines((c) => c.map((x, i) => i === idx ? { ...x, quantity: Number(e.target.value) } : x))} /></label>
                <label>Unit price<input type="number" min={0} step={0.01} value={line.unit_price} onChange={(e) => setLines((c) => c.map((x, i) => i === idx ? { ...x, unit_price: Number(e.target.value) } : x))} /></label>
              </div>
            ))}
            <div className="form-actions">
              <button type="button" className="button secondary" onClick={() => setLines((c) => [...c, { code: "SVC", description: "Additional service", quantity: 1, unit_price: 1000 }])}>+ Line</button>
              <button type="submit" disabled={busy}>{busy ? "Simulating…" : "Simulate coverage"}</button>
            </div>
          </div>
        </form>
      </article>
      {result && (
        <article className="card">
          <div className="row-between">
            <div>
              <h2>Result · {result.coverage_mode}</h2>
              <p className="muted">{result.eligibility_detail}</p>
            </div>
            <span className="status-pill">{result.eligibility}</span>
          </div>
          <div className="lab-summary">
            <div className="billing-line"><strong>Gross</strong><strong>{money(result.gross_total)}</strong></div>
            <div className="billing-line"><strong>Payer share</strong><strong>{money(result.payer_total)}</strong></div>
            <div className="billing-line"><strong>Patient share</strong><strong>{money(result.patient_total)}</strong></div>
            <div className="billing-line"><strong>Claimable</strong><strong>{result.claimable ? "Yes" : "No"}</strong></div>
          </div>
          <p><strong>Guidance:</strong> {result.guidance}</p>
          {result.warnings.length > 0 && (
            <div className="error">{result.warnings.map((w) => <div key={w}>{w}</div>)}</div>
          )}
          <div className="table-wrap">
            <table>
              <thead><tr><th>Service</th><th>Line</th><th>Payer</th><th>Patient</th><th>Note</th></tr></thead>
              <tbody>
                {result.lines.map((l) => (
                  <tr key={l.code + l.description}>
                    <td>{l.code}<br /><small>{l.description}</small></td>
                    <td>{money(l.line_total)}</td>
                    <td>{money(l.payer_share)}</td>
                    <td>{money(l.patient_share)}</td>
                    <td>{l.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      )}
    </section>
  );
}
