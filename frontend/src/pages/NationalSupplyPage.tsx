import { useEffect, useState } from "react";
import { getNationalSupply } from "../api/nationalSupplyApi";
import type { NationalSupplyItem } from "../api/nationalSupply";

function moneylessQuantity(value: number) { return value.toLocaleString("en-KE", { maximumFractionDigits: 2 }); }

export function NationalSupplyPage() {
  const [items, setItems] = useState<NationalSupplyItem[]>([]);
  const [county, setCounty] = useState("");
  const [medicationCode, setMedicationCode] = useState("");
  const [lowOnly, setLowOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [total, setTotal] = useState(0);

  async function load() {
    setLoading(true); setError("");
    try {
      const result = await getNationalSupply({ county, medicationCode, lowStockOnly: lowOnly });
      setItems(result.items); setTotal(result.total);
    } catch (err) { setError(err instanceof Error ? err.message : "NATIONAL_SUPPLY_REQUEST_FAILED"); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  return <section className="page-stack">
    <header className="page-heading">
      <div><p className="eyebrow">National health platform</p><h1>Medicine supply visibility</h1><p className="muted">Live facility inventory visibility for authorised supply operations. No patient records are exposed.</p></div>
      <button type="button" className="button secondary" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button>
    </header>
    <article className="card">
      <div className="filter-row">
        <label>County<input value={county} maxLength={100} placeholder="All counties" onChange={e => setCounty(e.target.value)} /></label>
        <label>Medicine code<input value={medicationCode} maxLength={50} placeholder="All medicines" onChange={e => setMedicationCode(e.target.value)} /></label>
        <label className="checkbox-label"><input type="checkbox" checked={lowOnly} onChange={e => setLowOnly(e.target.checked)} /> Low stock only</label>
        <button type="button" className="button filter-action" onClick={() => void load()} disabled={loading}>Apply filters</button>
      </div>
    </article>
    {error && <div className="error-banner" role="alert">{error === "PERMISSION_DENIED" ? "National supply visibility permission required." : error}</div>}
    <article className="card">
      <div className="card-header"><div><h2>Facility stock position</h2><p className="muted">{total.toLocaleString()} active inventory records match the current filters.</p></div></div>
      {loading ? <p className="muted">Loading national supply data…</p> : items.length === 0 ? <div className="empty-state"><strong>No inventory records found</strong><span>Adjust the filters or confirm that active facilities have inventory records.</span></div> : <div className="table-wrap"><table><thead><tr><th>Facility</th><th>Medicine</th><th>Current</th><th>Minimum</th><th>Non-expired</th><th>Expiring ≤30d</th><th>Next expiry</th><th>Status</th></tr></thead><tbody>{items.map(item => <tr key={`${item.facility_id}:${item.medication_id}`}><td><strong>{item.facility_name}</strong><div className="muted small">{item.facility_code} · {item.county || "Unspecified"}</div></td><td><strong>{item.medication_name}</strong><div className="muted small">{item.medication_code}</div></td><td>{moneylessQuantity(item.current_quantity)}</td><td>{moneylessQuantity(item.minimum_quantity)}</td><td>{moneylessQuantity(item.non_expired_batch_quantity)}</td><td>{moneylessQuantity(item.expiring_within_30_days_quantity)}</td><td>{item.next_expiry_date || "—"}</td><td>{item.low_stock ? <span className="status-pill status-warning">LOW STOCK</span> : <span className="status-pill status-success">OK</span>}</td></tr>)}</tbody></table></div>}
    </article>
  </section>;
}
