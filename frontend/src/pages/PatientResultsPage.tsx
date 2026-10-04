import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

type LabResult = {
  id: string;
  order_id: string;
  test_name: string;
  test_code: string;
  result: string;
  unit?: string | null;
  reference_range?: string | null;
  comments?: string | null;
  status: string;
  verified_at?: string | null;
  created_at: string;
};

type ImagingResult = {
  id: string;
  order_number: string;
  test_name: string;
  modality: string;
  findings: string;
  impression?: string | null;
  report_status: string;
  reported_at: string;
  reviewed_at?: string | null;
};

type ResultsResponse = {
  labs: LabResult[];
  imaging: ImagingResult[];
  total_labs: number;
  total_imaging: number;
};

export function PatientResultsPage() {
  const auth = useAuth();
  const [data, setData] = useState<ResultsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (auth.accountType !== "patient") return;
    api.portalResults()
      .then((value: ResultsResponse) => setData(value))
      .catch((e: unknown) =>
        setError(e instanceof ApiError ? e.message || e.code : "Unable to load results"),
      )
      .finally(() => setLoading(false));
  }, [auth.accountType]);

  if (!auth.ready) {
    return <div className="portal-page"><div className="portal-shell"><div className="portal-card"><p className="muted">Loading…</p></div></div></div>;
  }
  if (auth.accountType !== "patient") return <Navigate to="/login/patient" replace />;

  return (
    <div className="portal-page">
      <div className="portal-shell wide">
        <div className="portal-card">
          <div className="portal-brand">
            <KenyaFlag />
            <div><div className="brand-kicker">Patient portal</div><h1>My results</h1></div>
          </div>
          <p className="muted">Verified laboratory results and completed radiology reports from your care record.</p>

          {error && <div className="error" role="alert">{error}</div>}
          {loading && <p className="muted">Loading results…</p>}

          {!loading && data && (
            <>
              <section className="notice">
                <strong>{data.total_labs + data.total_imaging} result{data.total_labs + data.total_imaging === 1 ? "" : "s"}</strong>
                <div className="muted small">Only finalized/verified results are shown.</div>
              </section>

              <section style={{ marginTop: 16 }}>
                <h2>Laboratory</h2>
                {data.labs.length === 0 ? (
                  <p className="muted small">No verified laboratory results yet.</p>
                ) : (
                  <div className="portal-list">
                    {data.labs.map((lab) => (
                      <article key={lab.id} className="portal-list-item">
                        <strong>{lab.test_name}</strong>
                        <div className="muted small">{lab.test_code} · {lab.order_id} · {new Date(lab.created_at).toLocaleString()}</div>
                        <p style={{ marginBottom: 4 }}>
                          <strong>{lab.result}</strong>{lab.unit ? ` ${lab.unit}` : ""}
                          {lab.reference_range ? <span className="muted"> · Reference: {lab.reference_range}</span> : null}
                        </p>
                        {lab.comments && <div className="small muted">{lab.comments}</div>}
                        <div className="small muted">Status: {lab.status}{lab.verified_at ? ` · Verified ${new Date(lab.verified_at).toLocaleString()}` : ""}</div>
                      </article>
                    ))}
                  </div>
                )}
              </section>

              <section style={{ marginTop: 20 }}>
                <h2>Radiology / imaging</h2>
                {data.imaging.length === 0 ? (
                  <p className="muted small">No completed imaging reports yet.</p>
                ) : (
                  <div className="portal-list">
                    {data.imaging.map((item) => (
                      <article key={item.id} className="portal-list-item">
                        <strong>{item.test_name} · {item.modality}</strong>
                        <div className="muted small">{item.order_number} · {new Date(item.reported_at).toLocaleString()}</div>
                        <p><strong>Findings</strong></p>
                        <p className="small">{item.findings}</p>
                        {item.impression && <><p><strong>Impression</strong></p><p className="small">{item.impression}</p></>}
                        <div className="small muted">Report status: {item.report_status}{item.reviewed_at ? ` · Reviewed ${new Date(item.reviewed_at).toLocaleString()}` : ""}</div>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </>
          )}

          <div className="portal-footer-links"><Link to="/portal">Back to portal</Link></div>
        </div>
      </div>
    </div>
  );
}
