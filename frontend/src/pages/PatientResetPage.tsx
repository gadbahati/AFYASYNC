import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { KenyaFlag } from "../components/KenyaFlag";

export function PatientResetPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<"request" | "confirm">("request");
  const [identifier, setIdentifier] = useState("");
  const [channel, setChannel] = useState<"PHONE" | "EMAIL">("PHONE");
  const [hint, setHint] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onRequest(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setSubmitting(true);
    try {
      const res = await api.patientPasswordResetRequest(identifier.trim(), channel);
      setHint(res.destination_hint || "***");
      setMessage(res.message || "If an account exists, a code was sent.");
      setStep("confirm");
    } catch (err) {
      const codeErr = err instanceof ApiError ? err.code : "";
      if (codeErr === "NO_PHONE_ON_FILE") {
        setError("No phone number on file. Try email or contact your facility.");
      } else if (codeErr === "NO_EMAIL_ON_FILE") {
        setError("No email on file. Try phone or contact your facility.");
      } else {
        setError(err instanceof ApiError ? err.message || err.code : "Request failed.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function onConfirm(event: FormEvent) {
    event.preventDefault();
    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await api.patientPasswordResetConfirm(identifier.trim(), code.trim(), newPassword);
      navigate("/login/patient", { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.code === "INVALID_RESET_CODE"
            ? "Invalid or expired code. Request a new one."
            : err.message || err.code
          : "Could not reset password."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page" aria-label="Reset patient password">
      <div className="card auth-card">
        <div className="auth-brand">
          <KenyaFlag />
          <div>
            <div className="brand-kicker">Republic of Kenya</div>
            <h1>AfyaSync</h1>
          </div>
        </div>
        <div>
          <h2>Reset password</h2>
          <p className="muted">
            {step === "request"
              ? "We will send a one-time code to the phone or email on your record."
              : `Enter the code sent to ${hint} and choose a new password.`}
          </p>
        </div>

        {step === "request" ? (
          <form onSubmit={onRequest} noValidate>
            <label htmlFor="identifier">
              Afya ID or SHA number
              <input
                id="identifier"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                required
                autoCapitalize="none"
              />
            </label>
            <label htmlFor="channel">
              Send code to
              <select
                id="channel"
                value={channel}
                onChange={(e) => setChannel(e.target.value as "PHONE" | "EMAIL")}
              >
                <option value="PHONE">Phone (SMS)</option>
                <option value="EMAIL">Email</option>
              </select>
            </label>
            {error && (
              <div className="error" role="alert">
                {error}
              </div>
            )}
            <button type="submit" disabled={submitting || !identifier.trim()}>
              {submitting ? "Sending…" : "Send reset code"}
            </button>
          </form>
        ) : (
          <form onSubmit={onConfirm} noValidate>
            {message && <p className="muted small">{message}</p>}
            <label htmlFor="code">
              Reset code
              <input
                id="code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                inputMode="numeric"
                autoComplete="one-time-code"
              />
            </label>
            <label htmlFor="new_password">
              New password
              <input
                id="new_password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </label>
            <label htmlFor="confirm_password">
              Confirm new password
              <input
                id="confirm_password"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </label>
            {error && (
              <div className="error" role="alert">
                {error}
              </div>
            )}
            <button type="submit" disabled={submitting || !code || !newPassword}>
              {submitting ? "Updating…" : "Update password"}
            </button>
            <button
              type="button"
              className="linkish"
              style={{ marginTop: "0.75rem" }}
              onClick={() => {
                setStep("request");
                setError(null);
              }}
            >
              Request a new code
            </button>
          </form>
        )}

        <p className="muted small" style={{ marginTop: "1rem" }}>
          <Link to="/login/patient">Back to patient sign in</Link>
        </p>
      </div>
    </main>
  );
}
