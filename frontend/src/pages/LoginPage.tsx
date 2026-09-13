import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { getRememberedUsername, isRememberMeEnabled, setRememberMe } from "../auth/storage";
import { KenyaFlag } from "../components/KenyaFlag";

export function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState(getRememberedUsername() || "");
  const [password, setPassword] = useState("");
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
        <p className="muted">Secure staff sign-in to the AfyaSync healthcare platform.</p>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required placeholder="Enter your username" />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required placeholder="Enter your password" />
        </label>
        <label className="remember-row">
          <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
          <span>Keep me signed in on this device</span>
        </label>
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={submitting}>{submitting ? "Signing in…" : "Sign in"}</button>
        <p className="muted small auth-note">Authentication is handled by the AfyaSync API. Passwords are not stored in browser storage.</p>
      </form>
    </div>
  );
}
