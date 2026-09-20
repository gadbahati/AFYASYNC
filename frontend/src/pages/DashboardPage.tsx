import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { FacilityReport, Referral, Transfer } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { getAccessToken } from "../auth/storage";
import { KenyaFlag } from "../components/KenyaFlag";

export function DashboardPage() {
  const auth = useAuth();
  const [report, setReport] = useState<FacilityReport | null>(null);
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!auth.ready || !auth.username || !auth.facilityId || !getAccessToken()) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([api.facilityReport(), api.listReferrals("source"), api.listTransfers("source")])
      .then(([data, referralData, transferData]) => {
        if (cancelled) return;
        setReport(data);
        setReferrals(referralData.items);
        setTransfers(transferData.items);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message || err.code : "REPORT_LOAD_FAILED");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [auth.ready, auth.username, auth.facilityId]);

  return (
    <div className="dashboard">
      <section className="hero-banner">
        <div className="hero-left">
          <KenyaFlag className="kenya-crest large" />
          <div>
            <div className="brand-kicker">Republic of Kenya</div>
            <h1>Facility dashboard</h1>
            <p className="muted">
              <strong>{auth.facilityName || "Facility"}</strong> · live facility workspace
            </p>
          </div>
        </div>
        <div className="hero-actions">
          <Link className="button" to="/patients">
            Patients
          </Link>
          <Link className="button secondary" to="/referrals">
            Referrals & transfers
          </Link>
        </div>
      </section>

      {loading && <p className="muted">Loading facility workspace…</p>}
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}

      {report && (
        <>
          <h2 className="section-title">Service</h2>
          <div className="stat-grid">
            <StatLink
              label="Patients"
              value={report.patients}
              to="/patients"
              help="Registered patients and their complete facility records"
            />
            <StatLink
              label="Encounters"
              value={report.encounters}
              to="/encounters"
              help="Clinical visits, statuses and clinical records"
            />
            <StatLink
              label="Claims"
              value={report.claims}
              to="/claims"
              help="Claims, validation, responses and reconciliation"
            />
          </div>

          <section className="card monitor-panel">
            <h3>Referral & transfer monitor</h3>
            <p className="muted">
              This facility is the source for the following live referral and transfer requests.
            </p>
            <div className="stat-grid">
              <Stat label="Referrals sent" value={referrals.length} />
              <Stat
                label="Accepted referrals"
                value={referrals.filter((x) => x.status === "ACCEPTED" || x.status === "IN_PROGRESS").length}
              />
              <Stat
                label="Transfers accepted"
                value={transfers.filter((x) => x.status === "ACCEPTED").length}
              />
              <Stat
                label="Patients in transit"
                value={transfers.filter((x) => x.status === "IN_TRANSIT").length}
              />
            </div>
            {(referrals.length > 0 || transfers.length > 0) && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Reference</th>
                      <th>Type</th>
                      <th>Destination</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {referrals.slice(0, 6).map((row) => (
                      <tr key={`r-${row.id}`}>
                        <td>{row.referral_id}</td>
                        <td>Referral</td>
                        <td>{row.destination_facility_id}</td>
                        <td>
                          <span className="status-pill">{row.status}</span>
                        </td>
                      </tr>
                    ))}
                    {transfers.slice(0, 6).map((row) => (
                      <tr key={`t-${row.id}`}>
                        <td>{row.transfer_id}</td>
                        <td>Transfer</td>
                        <td>{row.destination_facility_id}</td>
                        <td>
                          <span className="status-pill">{row.status}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p style={{ marginBottom: 0 }}>
              <Link to="/referrals">Open referral & transfer workspace →</Link>
            </p>
          </section>

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
            <h3>Operational areas</h3>
            <p className="muted">
              Open a clinical or financing workspace to work with live facility records.
            </p>
            <p style={{ marginBottom: 0, lineHeight: 1.8 }}>
              <Link to="/patients">Patients</Link>
              {" · "}
              <Link to="/encounters">Encounters</Link>
              {" · "}
              <Link to="/appointments">Appointments</Link>
              {" · "}
              <Link to="/queue">Clinical queue</Link>
              {" · "}
              <Link to="/mch">MCH</Link>
              {" · "}
              <Link to="/laboratory">Lab</Link>
              {" · "}
              <Link to="/pharmacy">Pharmacy</Link>
              {" · "}
              <Link to="/billing">Billing</Link>
              {" · "}
              <Link to="/claims">Claims & rework</Link>
              {" · "}
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
  return Number.isNaN(n) ? String(value) : new Intl.NumberFormat("en-KE").format(n);
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="stat-card">
      <div className="muted small">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function StatLink({
  label,
  value,
  to,
  help,
}: {
  label: string;
  value: string | number;
  to: string;
  help: string;
}) {
  return (
    <Link to={to} className="stat-card stat-card-link" aria-label={`${label}: ${value}. ${help}`}>
      <div className="muted small">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="small muted">{help} →</div>
    </Link>
  );
}

function ReportTable({
  title,
  headers,
  rows,
  empty,
}: {
  title: string;
  headers: string[];
  rows: string[][];
  empty: string;
}) {
  return (
    <section className="card report-card">
      <div className="report-card-header">
        <div>
          <h3 style={{ margin: 0 }}>{title}</h3>
          <p className="muted small">Calculated from facility records for the selected reporting window.</p>
        </div>
      </div>
      {rows.length === 0 ? (
        <p className="muted">{empty}</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {headers.map((header) => (
                  <th key={header}>{header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`${row[0]}-${index}`}>
                  {row.map((cell, cellIndex) => (
                    <td key={`${cell}-${cellIndex}`}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
