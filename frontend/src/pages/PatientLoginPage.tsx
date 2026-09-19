import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

/** Universal test patient — replace when production API is live */
export const TEST_PATIENT_ID = "AFYA-TEST-001";
export const TEST_PATIENT_PASSWORD = "TestPatient@2026";

export function PatientLoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState(TEST_PATIENT_ID);
  const [password, setPassword] = useState(TEST_PATIENT_PASSWORD);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!auth.ready) {
    return (
      <div className="auth-page">
        <div className="card auth-card">
          <p className="muted">Checking your secure session…</p>
        </div>
      </div>
    );
  }

  if (auth.username && auth.accountType === "patient") {
    return <Navigate to="/portal" replace />;
  }
  if (auth.username && auth.facilityId) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const id = identifier.trim();
    if (!id || !password) return;
    setError(null);
    setSubmitting(true);
    try {
      await auth.patientLogin(id, password);
      navigate("/portal", { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message || err.code || "Unable to sign in"
          : "Unable to sign in. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page" aria-label="Patient sign in">
      <form className="card auth-card" onSubmit={onSubmit} noValidate>
        <div className="auth-brand">
          <KenyaFlag />
          <div>
            <div className="brand-kicker">Republic of Kenya</div>
            <h1>AfyaSync</h1>
          </div>
        </div>
        <div>
          <h2>Patient sign in</h2>
          <p className="muted">Use your Afya ID or SHA membership number.</p>
        </div>

        <div className="info-box">
          <strong>Test login (temporary)</strong>
          <p className="small" style={{ margin: "0.35rem 0 0" }}>
            ID: <strong>{TEST_PATIENT_ID}</strong>
            <br />
            Password: <strong>{TEST_PATIENT_PASSWORD}</strong>
          </p>
          <p className="muted small" style={{ margin: "0.35rem 0 0" }}>
            Pre-filled for pilot testing. Change when production API is connected.
          </p>
        </div>

        <label htmlFor="identifier">
          Afya ID or SHA number
          <input
            id="identifier"
            name="identifier"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            required
            placeholder="e.g. AFYA-… or SHA membership number"
          />
        </label>
        <label htmlFor="password">
          Password
          <input
            id="password"
            name="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            placeholder="Enter your password"
          />
        </label>

        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}

        <button type="submit" disabled={submitting || !identifier.trim() || !password}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>

        <p className="muted small" style={{ marginTop: "1rem" }}>
          <Link to="/login/patient/register">Create patient account</Link>
          {" · "}
          <Link to="/login/patient/reset">Forgot password</Link>
          {" · "}
          <Link to="/login">Back</Link>
        </p>

        <p className="muted small auth-note">
          © {new Date().getFullYear()} AfyaSync. Developed by <strong>BAHATI GAD WANGWE</strong>.
        </p>
      </form>
    </main>
  );
}
