import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { BenefitPackage } from "../api/types";

export function BenefitPackagesPage() {
  const [packages, setPackages] = useState<BenefitPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void api.listBenefitPackages()
      .then((data) => {
        if (active) setPackages(data);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setError(err instanceof ApiError ? err.message : "Unable to load benefit packages.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">SHA benefits</p>
          <h1>Benefit packages</h1>
          <p className="muted">Live benefit definitions available to the selected facility.</p>
        </div>
      </div>

      {loading && <div className="card">Loading benefit packages…</div>}
      {error && <div className="card error">{error}</div>}
      {!loading && !error && packages.length === 0 && (
        <div className="card">No active benefit packages are configured.</div>
      )}

      <div className="card-grid">
        {packages.map((item) => (
          <article className="card" key={item.id}>
            <div className="row-between">
              <span className="badge">{item.package_code}</span>
              <span className="muted small">{item.payer_code}</span>
            </div>
            <h2>{item.name}</h2>
            <p>{item.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
