import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { FacilityReport } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

export function DashboardPage() {
  const auth = useAuth();
  const [report, setReport] = useState<FacilityReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .facilityReport()
      .then((data) => {
        if (!cancelled) setReport(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.code : "REPORT_LOAD_FAILED");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="dashboard">
      <section className="hero-banner">
        <div className="hero-left">
          <KenyaFlag className="kenya-flag large" />
          <div>
            <div className="brand-kicker">Ministry of Health aligned · National digital health</div>
            <h1>Facility operations dashboard</h1>
            <p className="muted">
              {auth.facilityName || "Selected facility"} · Performance overview (last 30 days)
            </p>
          </div>
        </div>
        <div className="hero-actions">
          <Link className="button" to="/patients">Patient register</Link>
          <Link className="button secondary" to="/patients/new">Register patient</Link>
        </div>
      </section>

      {loading && <p>Loading facility metrics…</p>}
      {error && (
        <div className="error">
          {error}
          {error === "REQUEST_FAILED" || error.includes("Failed")
            ? " — API may be offline. Deploy the backend and set VITE_API_BASE_URL."
            : null}
        </div>
      )}

      {report && (
        <>
          <h2 className="section-title">Service activity</h2>
          <div className="stat-grid">
            <Stat label="Active patient activity" value={report.patients} tone="primary" />
            <Stat label="Encounters" value={report.encounters} tone="primary" />
            <Stat label="Claims submitted" value={report.claims} />
          </div>

          <h2 className="section-title">Financial integrity</h2>
          <div className="stat-grid">
            <Stat label="Charges total" value={formatMoney(report.charges_total)} />
            <Stat label="Invoices total" value={formatMoney(report.invoices_total)} />
            <Stat label="Payer billed" value={formatMoney(report.payer_billed)} />
            <Stat label="Patient billed" value={formatMoney(report.patient_billed)} />
            <Stat label="Confirmed payments" value={formatMoney(report.confirmed_payments)} tone="success" />
            <Stat label="Claims amount" value={formatMoney(report.claims_amount)} />
            <Stat label="Claims approved" value={formatMoney(report.claims_approved)} />
            <Stat label="Claims paid" value={formatMoney(report.claims_paid)} tone="success" />
          </div>

          <section className="card monitor-panel">
            <h3>System monitoring</h3>
            <p className="muted">
              Signed in as <strong>{auth.username}</strong>. Metrics are facility-scoped and drawn from live
              AfyaSync APIs (encounters, billing, claims). Use this view to track pilot facility throughput
              and payer reconciliation progress.
            </p>
          </section>
        </>
      )}
    </div>
  );
}

function formatMoney(value: string | number): string {
  const n = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(n)) return String(value);
  return new Intl.NumberFormat("en-KE", { style: "currency", currency: "KES", maximumFractionDigits: 0 }).format(n);
}

function Stat({ label, value, tone }: { label: string; value: string | number; tone?: "primary" | "success" }) {
  return (
    <div className={`stat-card ${tone || ""}`}>
      <div className="muted small">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}
