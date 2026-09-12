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

  if (auth.ready && auth.username && auth.facilityId) {
    return <Navigate to="/" replace />;
  }
  if (auth.pendingFacilities) {
    return <Navigate to="/select-facility" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      setRememberMe(remember, username.trim());
      const result = await auth.login(username.trim(), password);
      navigate(result === "select_facility" ? "/select-facility" : "/");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || err.code);
      } else {
        setError("LOGIN_FAILED");
      }
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
            <div className="brand-kicker">Republic of Kenya · Health Information</div>
            <h1>AfyaSync</h1>
          </div>
        </div>
        <p className="muted">
          Secure staff console for facility-scoped clinical, billing, and claims operations.
        </p>
        <label>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
            placeholder="afyasync.admin"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <label className="remember-row">
          <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
          <span>Remember me on this device</span>
        </label>
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={submitting}>{submitting ? "Signing in…" : "Sign in"}</button>
        <p className="muted small auth-note">
          Demo account (after API is online): <strong>afyasync.admin</strong> / <strong>Kenya@Health2026</strong>
        </p>
      </form>
    </div>
  );
}
