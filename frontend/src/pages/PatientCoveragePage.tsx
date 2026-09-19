import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

type CoverageItem = {
  id?: string;
  payer_name?: string | null;
  coverage_mode?: string | null;
  membership_number?: string | null;
  status?: string | null;
  verification_status?: string | null;
};

export function PatientCoveragePage() {
  const auth = useAuth();
  const [items, setItems] = useState<CoverageItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (auth.accountType !== "patient") return;
    setLoading(true);
    api
      .portalCoverage()
      .then((res: any) => setItems(res.items || []))
      .catch((e: unknown) =>
        setError(e instanceof ApiError ? e.message || e.code : "Unable to load coverage"),
      )
      .finally(() => setLoading(false));
  }, [auth.accountType]);

  if (!auth.ready) {
    return (
      <div className="portal-page">
        <div className="portal-shell">
          <div className="portal-card">
            <p className="muted">Loading…</p>
          </div>
        </div>
      </div>
    );
  }
  if (auth.accountType !== "patient") return <Navigate to="/login/patient" replace />;

  return (
    <div className="portal-page">
      <div className="portal-shell wide">
        <div className="portal-card">
          <div className="portal-brand">
            <KenyaFlag />
            <div>
              <div className="brand-kicker">Patient portal</div>
              <h1>My coverage</h1>
            </div>
          </div>
          <p className="muted">SHA and other memberships linked to your AfyaSync identity.</p>

          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}

          {loading ? (
            <p className="muted">Loading coverage…</p>
          ) : items.length === 0 ? (
            <div className="info-box">
              No coverage records found on your profile yet. Ask the facility registration desk to
              link your SHA membership number during your next visit.
            </div>
          ) : (
            <ul className="portal-list">
              {items.map((c, i) => (
                <li key={c.id || String(i)} className="portal-list-item">
                  <strong>{c.payer_name || "Health cover"}</strong>
                  <p className="muted small">
                    {c.membership_number ? `Member: ${c.membership_number}` : "Membership number not shown"}
                  </p>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 6 }}>
                    {c.status && (
                      <span className="portal-status accepted">{c.status}</span>
                    )}
                    {c.verification_status && (
                      <span className="status-pill">{c.verification_status}</span>
                    )}
                    {c.coverage_mode && (
                      <span className="muted small">{c.coverage_mode}</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          <div className="portal-footer-links">
            <Link to="/portal">Back to portal</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
