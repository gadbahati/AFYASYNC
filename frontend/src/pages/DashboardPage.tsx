import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { FacilityReport } from "../api/types";
import { useAuth } from "../auth/AuthContext";

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
    <div>
      <header className="page-header">
        <div>
          <h1>Facility dashboard</h1>
          <p className="muted">{auth.facilityName} · last 30 days</p>
        </div>
      </header>

      {loading && <p>Loading report…</p>}
      {error && <div className="error">{error}</div>}

      {report && (
        <div className="stat-grid">
          <Stat label="Patients (enrolled activity)" value={report.patients} />
          <Stat label="Encounters" value={report.encounters} />
          <Stat label="Charges total" value={report.charges_total} />
          <Stat label="Invoices total" value={report.invoices_total} />
          <Stat label="Payer billed" value={report.payer_billed} />
          <Stat label="Patient billed" value={report.patient_billed} />
          <Stat label="Confirmed payments" value={report.confirmed_payments} />
          <Stat label="Claims" value={report.claims} />
          <Stat label="Claims amount" value={report.claims_amount} />
          <Stat label="Claims approved" value={report.claims_approved} />
          <Stat label="Claims paid" value={report.claims_paid} />
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="stat-card">
      <div className="muted small">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}
