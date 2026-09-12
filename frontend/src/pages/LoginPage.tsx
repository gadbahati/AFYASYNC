import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { getRememberedUsername, isRememberMeEnabled, setRememberMe } from "../auth/storage";
import { KenyaFlag } from "../components/KenyaFlag";

// Controlled pilot/demo account. The password is never persisted in browser storage.
// For a real production deployment, replace the backend bootstrap credentials through secrets.
const UNIVERSAL_USERNAME = "afyasync.admin";
const UNIVERSAL_PASSWORD = "Kenya@Health2026";

export function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState(getRememberedUsername() || UNIVERSAL_USERNAME);
  const [password, setPassword] = useState(UNIVERSAL_PASSWORD);
  const [remember, setRemember] = useState(isRememberMeEnabled());
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (auth.ready && auth.username && auth.facilityId) return <Navigate to="/" replace />;
  if (auth.pendingFacilities) return <Navigate to="/select-facility" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      setRememberMe(remember, username.trim());
      const result = await auth.login(username.trim(), password);
      navigate(result === "select_facility" ? "/select-facility" : "/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "LOGIN_FAILED");
    } finally {
      setSubmitting(false);
    }
  }

  function useUniversalAccount() {
    setUsername(UNIVERSAL_USERNAME);
    setPassword(UNIVERSAL_PASSWORD);
    setError(null);
  }

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={onSubmit}>
        <div className="auth-brand">
          <KenyaFlag />
          <div>
            <div className="brand-kicker">Republic of Kenya</div>
            <h1>AfyaSync</h1>
          </div>
        </div>
        <p className="muted">Universal staff sign-in. Use the same account whenever you return to AfyaSync.</p>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required placeholder="afyasync.admin" />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </label>
        <label className="remember-row">
          <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
          <span>Keep me signed in on this device</span>
        </label>
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={submitting}>{submitting ? "Signing in…" : "Sign in"}</button>
        <button type="button" className="button secondary" onClick={useUniversalAccount}>Use universal account</button>
        <div className="notice auth-note">
          <strong>Pilot account</strong>
          <div className="small muted">Username: {UNIVERSAL_USERNAME}</div>
          <div className="small muted">Password: {UNIVERSAL_PASSWORD}</div>
        </div>
        <p className="muted small auth-note">The live account is authenticated by the AfyaSync API. The browser remembers the username and session when selected; the password is not stored in browser storage.</p>
      </form>
    </div>
  );
}
