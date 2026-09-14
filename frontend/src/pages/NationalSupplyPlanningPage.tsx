import { useEffect, useState } from "react";
import { getNationalSupplyPlanning } from "../api/nationalSupplyPlanningApi";
import type { SupplyReplenishmentRecommendation } from "../api/nationalSupplyPlanning";

const qty = (value: number) => value.toLocaleString("en-KE", { maximumFractionDigits: 2 });

export function NationalSupplyPlanningPage() {
  const [recommendations, setRecommendations] = useState<SupplyReplenishmentRecommendation[]>([]);
  const [county, setCounty] = useState("");
  const [medicationCode, setMedicationCode] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try { const result = await getNationalSupplyPlanning({ county, medicationCode }); setRecommendations(result.recommendations); }
    catch (err) { setError(err instanceof Error ? err.message : "NATIONAL_SUPPLY_PLANNING_FAILED"); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  return <section className="page-stack">
    <header className="page-heading">
      <div><p className="eyebrow">National health platform</p><h1>Supply replenishment planning</h1><p className="muted">Live, read-only recommendations for balancing medicine stock between active facilities. No transfer is executed automatically.</p></div>
      <button type="button" className="button secondary" disabled={loading} onClick={() => void load()}>{loading ? "Planning…" : "Refresh plan"}</button>
    </header>
    <article className="card"><div className="filter-row">
      <label>County<input value={county} maxLength={100} placeholder="All counties" onChange={e => setCounty(e.target.value)} /></label>
      <label>Medicine code<input value={medicationCode} maxLength={50} placeholder="All medicines" onChange={e => setMedicationCode(e.target.value)} /></label>
      <button type="button" className="button filter-action" disabled={loading} onClick={() => void load()}>Generate plan</button>
    </div></article>
    {error && <div className="error-banner" role="alert">{error === "PERMISSION_DENIED" ? "National supply planning permission required." : error}</div>}
    <article className="card"><div className="card-header"><div><h2>Replenishment recommendations</h2><p className="muted">Recommendations are calculated from current stock and minimum levels only.</p></div></div>
      {loading ? <p className="muted">Calculating from live inventory…</p> : recommendations.length === 0 ? <div className="empty-state"><strong>No actionable replenishment found</strong><span>There may be no shortages with transferable surplus under the current filters.</span></div> : <div className="table-wrap"><table><thead><tr><th>Receiving facility</th><th>Medicine</th><th>Current</th><th>Minimum</th><th>Shortage</th><th>Suggested transfer</th><th>Potential donor</th></tr></thead><tbody>{recommendations.map(item => <tr key={`${item.facility_id}:${item.medication_id}`}><td><strong>{item.facility_name}</strong><div className="muted small">{item.facility_code} · {item.county || "Unspecified"}</div></td><td><strong>{item.medication_name}</strong><div className="muted small">{item.medication_code}</div></td><td>{qty(item.current_quantity)}</td><td>{qty(item.minimum_quantity)}</td><td>{qty(item.shortage_quantity)}</td><td>{qty(item.suggested_transfer_quantity)}</td><td>{item.donors.length === 0 ? "—" : item.donors.map(d => `${d.facility_name} (${qty(d.available_surplus)})`).join(", ")}</td></tr>)}</tbody></table></div>}
    </article>
  </section>;
}
