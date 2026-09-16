import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { getAccessToken } from "../auth/storage";

type CarePlan = {
  id: string;
  patient_id: string;
  facility_id: string;
  encounter_id: string | null;
  created_by: string;
  title: string;
  goals: string | null;
  interventions: string | null;
  clinical_notes: string | null;
  target_date: string | null;
  status: "ACTIVE" | "COMPLETED" | "CANCELLED";
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

type Patient = { id: string; afya_id: string; first_name: string; middle_name: string | null; last_name: string };

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "API_UNREACHABLE");
  }
  if (!response.ok) {
    let body: { detail?: string | { code?: string; message?: string } } = {};
    try { body = await response.json(); } catch { /* empty */ }
    const detail = body.detail;
    const code = typeof detail === "string" ? detail : detail?.code || `HTTP_${response.status}`;
    const message = typeof detail === "string" ? detail : detail?.message;
    throw new ApiError(response.status, code, message);
  }
  return response.json() as Promise<T>;
}

export function CarePlansPage() {
  const { patientId } = useParams();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [plans, setPlans] = useState<CarePlan[]>([]);
  const [status, setStatus] = useState<"ALL" | "ACTIVE" | "COMPLETED" | "CANCELLED">("ALL");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!patientId) return;
    const query = status === "ALL" ? "" : `?status=${status}`;
    const [patientData, planData] = await Promise.all([
      request<Patient>(`/api/v1/patients/${patientId}`),
      request<CarePlan[]>(`/api/v1/patients/${patientId}/care-plans${query}`),
    ]);
    setPatient(patientData);
    setPlans(planData);
  }, [patientId, status]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    reload().catch((err) => {
      if (!cancelled) setError(err instanceof ApiError ? err.code : "LOAD_FAILED");
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [reload]);

  async function createPlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!patientId) return;
    const form = new FormData(event.currentTarget);
    const payload = {
      title: String(form.get("title") || "").trim(),
      goals: String(form.get("goals") || "").trim() || null,
      interventions: String(form.get("interventions") || "").trim() || null,
      clinical_notes: String(form.get("clinical_notes") || "").trim() || null,
      target_date: String(form.get("target_date") || "").trim() || null,
    };
    setBusy(true);
    setError(null);
    try {
      await request<CarePlan>(`/api/v1/patients/${patientId}/care-plans`, { method: "POST", body: JSON.stringify(payload) });
      event.currentTarget.reset();
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "CREATE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(plan: CarePlan, nextStatus: "COMPLETED" | "CANCELLED") {
    setBusy(true);
    setError(null);
    try {
      await request<CarePlan>(`/api/v1/patients/${plan.patient_id}/care-plans/${plan.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      });
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "UPDATE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <Link to={patientId ? `/patients/${patientId}` : "/patients"} className="muted">← Patient</Link>
          <h1>Care plans</h1>
          <p className="muted">Longitudinal care coordination for {patient ? `${patient.first_name} ${patient.last_name}` : "this patient"}.</p>
        </div>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value as typeof status)}>
            <option value="ALL">All</option>
            <option value="ACTIVE">Active</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </label>
      </header>

      {loading && <p>Loading care plans…</p>}
      {error && <div className="error">{error}</div>}

      <div className="stack">
        <section className="card">
          <h2>New care plan</h2>
          <form className="form-grid" onSubmit={createPlan}>
            <label className="full">Title <input name="title" required minLength={2} maxLength={200} placeholder="e.g. Hypertension follow-up" /></label>
            <label className="full">Goals <textarea name="goals" rows={3} maxLength={10000} /></label>
            <label className="full">Interventions <textarea name="interventions" rows={3} maxLength={10000} /></label>
            <label className="full">Clinical notes <textarea name="clinical_notes" rows={3} maxLength={10000} /></label>
            <label>Target date <input name="target_date" type="date" /></label>
            <div className="full actions"><button type="submit" disabled={busy}>Create care plan</button></div>
          </form>
        </section>

        <section className="card">
          <h2>Care plan history</h2>
          {plans.length === 0 && <p className="muted">No care plans match this filter.</p>}
          <div className="stack">
            {plans.map((plan) => (
              <article key={plan.id} className="card">
                <div className="page-header">
                  <div>
                    <h3>{plan.title}</h3>
                    <p className="muted small">{plan.status}{plan.target_date ? ` · target ${new Date(`${plan.target_date}T00:00:00`).toLocaleDateString()}` : ""}</p>
                  </div>
                  {plan.status === "ACTIVE" && (
                    <div className="actions">
                      <button type="button" disabled={busy} onClick={() => void changeStatus(plan, "COMPLETED")}>Complete</button>
                      <button type="button" disabled={busy} onClick={() => void changeStatus(plan, "CANCELLED")}>Cancel</button>
                    </div>
                  )}
                </div>
                <div className="detail-grid">
                  <Field label="Goals" value={plan.goals} />
                  <Field label="Interventions" value={plan.interventions} />
                  <Field label="Clinical notes" value={plan.clinical_notes} />
                  <Field label="Created" value={new Date(plan.created_at).toLocaleString()} />
                  {plan.completed_at && <Field label="Completed" value={new Date(plan.completed_at).toLocaleString()} />}
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | null }) {
  return <div><div className="muted small">{label}</div><div>{value || "—"}</div></div>;
}
