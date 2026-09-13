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
    api.facilityReport().then((data) => {
      if (!cancelled) setReport(data);
    }).catch((err) => {
      if (!cancelled) setError(err instanceof ApiError ? err.message || err.code : "REPORT_LOAD_FAILED");
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="dashboard">
      <section className="hero-banner">
        <div className="hero-left">
          <KenyaFlag className="kenya-flag large" />
          <div>
            <div className="brand-kicker">Republic of Kenya</div>
            <h1>Facility dashboard</h1>
            <p className="muted">{auth.facilityName || "Facility"} · last 30 days</p>
          </div>
        </div>
        <div className="hero-actions">
          <Link className="button" to="/patients">Patients</Link>
          <Link className="button secondary" to="/appointments">Appointments</Link>
        </div>
      </section>

      {loading && <p>Loading…</p>}
      {error && <div className="error">{error}</div>}

      {report && (
        <>
          <h2 className="section-title">Service</h2>
          <div className="stat-grid">
            <Stat label="Patients" value={report.patients} />
            <Stat label="Encounters" value={report.encounters} />
            <Stat label="Claims" value={report.claims} />
          </div>

          <h2 className="section-title">Money (KES)</h2>
          <div className="stat-grid">
            <Stat label="Charges" value={formatMoney(report.charges_total)} />
            <Stat label="Invoices" value={formatMoney(report.invoices_total)} />
            <Stat label="Payer billed" value={formatMoney(report.payer_billed)} />
            <Stat label="Patient billed" value={formatMoney(report.patient_billed)} />
            <Stat label="Payments confirmed" value={formatMoney(report.confirmed_payments)} />
            <Stat label="Claims amount" value={formatMoney(report.claims_amount)} />
            <Stat label="Claims approved" value={formatMoney(report.claims_approved)} />
            <Stat label="Claims paid" value={formatMoney(report.claims_paid)} />
            <Stat label="Payer receivable" value={formatMoney(report.claims_receivable)} />
          </div>

          <section className="report-grid">
            <ReportTable
              title="Claims by status"
              headers={["Status", "Claims", "Billed", "Approved", "Paid"]}
              rows={report.claim_statuses.map((item) => [
                item.status,
                String(item.count),
                formatMoney(item.amount),
                formatMoney(item.approved_amount),
                formatMoney(item.paid_amount),
              ])}
              empty="No claims were updated in this period."
            />
            <ReportTable
              title="Payer performance"
              headers={["Payer", "Claims", "Billed", "Approved", "Receivable"]}
              rows={report.payer_claims.map((item) => [
                item.payer_name,
                String(item.claims),
                formatMoney(item.amount),
                formatMoney(item.approved_amount),
                formatMoney(item.receivable),
              ])}
              empty="No payer claims were recorded in this period."
            />
          </section>

          <section className="card monitor-panel">
            <h3 style={{ marginTop: 0 }}>Operational areas</h3>
            <p className="muted" style={{ marginBottom: 8 }}>
              Open a clinical or financing workspace to work with live facility records.
            </p>
            <p>
              <Link to="/patients">Patients</Link>{" · "}
              <Link to="/appointments">Appointments</Link>{" · "}
              <Link to="/queue">Clinical queue</Link>{" · "}
              <Link to="/laboratory">Lab</Link>{" · "}
              <Link to="/pharmacy">Pharmacy</Link>{" · "}
              <Link to="/billing">Billing</Link>{" · "}
              <Link to="/claims">Claims &amp; rework</Link>{" · "}
              <Link to="/referrals">Referrals</Link>
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
  return new Intl.NumberFormat("en-KE").format(n);
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="stat-card">
      <div className="muted small">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function ReportTable({ title, headers, rows, empty }: { title: string; headers: string[]; rows: string[][]; empty: string }) {
  return (
    <section className="card report-card">
      <div className="report-card-header">
        <div>
          <h3 style={{ margin: 0 }}>{title}</h3>
          <p className="muted small">Calculated from facility records for the selected reporting window.</p>
        </div>
      </div>
      {rows.length === 0 ? <p className="muted">{empty}</p> : (
        <div className="table-wrap">
          <table>
            <thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead>
            <tbody>{rows.map((row, index) => (
              <tr key={`${row[0]}-${index}`}>{row.map((cell, cellIndex) => <td key={`${cell}-${cellIndex}`}>{cell}</td>)}</tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}
