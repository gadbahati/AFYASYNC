import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { ClinicalTimeline } from "../api/types";

export function EncounterDetailPage() {
  const { encounterId } = useParams();
  const [timeline, setTimeline] = useState<ClinicalTimeline | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    if (!encounterId) return;
    const data = await api.getClinicalTimeline(encounterId);
    setTimeline(data);
  }, [encounterId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    reload()
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.code : "LOAD_FAILED");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reload]);

  async function closeEncounter() {
    if (!encounterId || !timeline || timeline.encounter.status !== "OPEN") return;
    setBusy(true);
    setError(null);
    try {
      await api.closeEncounter(encounterId);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "CLOSE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onVitals(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!encounterId) return;
    const fd = new FormData(e.currentTarget);
    const num = (key: string) => {
      const raw = String(fd.get(key) || "").trim();
      return raw ? Number(raw) : null;
    };
    setBusy(true);
    setError(null);
    try {
      await api.recordVitals(encounterId, {
        systolic_bp: num("systolic_bp"),
        diastolic_bp: num("diastolic_bp"),
        pulse: num("pulse"),
        temperature_c: num("temperature_c"),
        respiratory_rate: num("respiratory_rate"),
        oxygen_saturation: num("oxygen_saturation"),
        weight_kg: num("weight_kg"),
        height_cm: num("height_cm"),
      });
      e.currentTarget.reset();
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "VITALS_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onConsultation(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!encounterId) return;
    const fd = new FormData(e.currentTarget);
    const text = (key: string) => {
      const raw = String(fd.get(key) || "").trim();
      return raw || null;
    };
    setBusy(true);
    setError(null);
    try {
      await api.saveConsultation(encounterId, {
        chief_complaint: text("chief_complaint"),
        history: text("history"),
        examination: text("examination"),
        assessment: text("assessment"),
        clinical_notes: text("clinical_notes"),
        treatment_plan: text("treatment_plan"),
      });
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "CONSULTATION_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onDiagnosis(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!encounterId) return;
    const fd = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await api.addDiagnosis(encounterId, {
        diagnosis_name: String(fd.get("diagnosis_name") || "").trim(),
        diagnosis_code: String(fd.get("diagnosis_code") || "").trim() || null,
        diagnosis_type: String(fd.get("diagnosis_type") || "PRIMARY"),
      });
      e.currentTarget.reset();
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "DIAGNOSIS_FAILED");
    } finally {
      setBusy(false);
    }
  }

  const open = timeline?.encounter.status === "OPEN";

  return (
    <div>
      <header className="page-header">
        <div>
          <Link to={timeline ? `/patients/${timeline.encounter.patient_id}` : "/patients"} className="muted">
            ← Patient
          </Link>
          <h1>Encounter {timeline?.encounter.encounter_id || ""}</h1>
          <p className="muted">
            {timeline
              ? `${timeline.encounter.encounter_type} · ${timeline.encounter.status}`
              : "Clinical timeline"}
          </p>
        </div>
        {open && (
          <button type="button" disabled={busy} onClick={() => void closeEncounter()}>
            Close encounter
          </button>
        )}
      </header>

      {loading && <p>Loading clinical timeline…</p>}
      {error && <div className="error">{error}</div>}

      {timeline && (
        <div className="stack">
          <section className="card">
            <h2>Vitals</h2>
            {timeline.vitals.length === 0 && <p className="muted">No vitals recorded yet.</p>}
            <ul className="plain-list">
              {timeline.vitals.map((v) => (
                <li key={v.id}>
                  {new Date(v.recorded_at).toLocaleString()} — BP {v.systolic_bp ?? "—"}/{v.diastolic_bp ?? "—"},
                  pulse {v.pulse ?? "—"}, temp {v.temperature_c ?? "—"}°C, SpO₂ {v.oxygen_saturation ?? "—"}%
                </li>
              ))}
            </ul>
            {open && (
              <form className="form-grid" onSubmit={onVitals}>
                <label>Systolic <input name="systolic_bp" type="number" /></label>
                <label>Diastolic <input name="diastolic_bp" type="number" /></label>
                <label>Pulse <input name="pulse" type="number" /></label>
                <label>Temp °C <input name="temperature_c" type="number" step="0.1" /></label>
                <label>Resp rate <input name="respiratory_rate" type="number" /></label>
                <label>SpO₂ % <input name="oxygen_saturation" type="number" step="0.1" /></label>
                <label>Weight kg <input name="weight_kg" type="number" step="0.1" /></label>
                <label>Height cm <input name="height_cm" type="number" step="0.1" /></label>
                <div className="full actions">
                  <button type="submit" disabled={busy}>Record vitals</button>
                </div>
              </form>
            )}
          </section>

          <section className="card">
            <h2>Consultation</h2>
            {timeline.consultation ? (
              <div className="detail-grid">
                <Field label="Chief complaint" value={timeline.consultation.chief_complaint} />
                <Field label="History" value={timeline.consultation.history} />
                <Field label="Examination" value={timeline.consultation.examination} />
                <Field label="Assessment" value={timeline.consultation.assessment} />
                <Field label="Notes" value={timeline.consultation.clinical_notes} />
                <Field label="Plan" value={timeline.consultation.treatment_plan} />
              </div>
            ) : (
              <p className="muted">No consultation saved yet.</p>
            )}
            {open && (
              <form className="form-grid" onSubmit={onConsultation}>
                <label className="full">Chief complaint <input name="chief_complaint" defaultValue={timeline.consultation?.chief_complaint || ""} /></label>
                <label className="full">History <textarea name="history" rows={2} defaultValue={timeline.consultation?.history || ""} /></label>
                <label className="full">Examination <textarea name="examination" rows={2} defaultValue={timeline.consultation?.examination || ""} /></label>
                <label className="full">Assessment <textarea name="assessment" rows={2} defaultValue={timeline.consultation?.assessment || ""} /></label>
                <label className="full">Clinical notes <textarea name="clinical_notes" rows={2} defaultValue={timeline.consultation?.clinical_notes || ""} /></label>
                <label className="full">Treatment plan <textarea name="treatment_plan" rows={2} defaultValue={timeline.consultation?.treatment_plan || ""} /></label>
                <div className="full actions">
                  <button type="submit" disabled={busy}>Save consultation</button>
                </div>
              </form>
            )}
          </section>

          <section className="card">
            <h2>Diagnoses</h2>
            <ul className="plain-list">
              {timeline.diagnoses.map((d) => (
                <li key={d.id}>{d.diagnosis_type}: {d.diagnosis_name} {d.diagnosis_code ? `(${d.diagnosis_code})` : ""}</li>
              ))}
              {timeline.diagnoses.length === 0 && <li className="muted">No diagnoses yet.</li>}
            </ul>
            {open && (
              <form className="form-grid" onSubmit={onDiagnosis}>
                <label>Name <input name="diagnosis_name" required /></label>
                <label>Code <input name="diagnosis_code" /></label>
                <label>
                  Type
                  <select name="diagnosis_type" defaultValue="PRIMARY">
                    <option value="PRIMARY">Primary</option>
                    <option value="SECONDARY">Secondary</option>
                  </select>
                </label>
                <div className="full actions">
                  <button type="submit" disabled={busy}>Add diagnosis</button>
                </div>
              </form>
            )}
          </section>

          <section className="card">
            <h2>Linked orders</h2>
            <p className="muted small">Lab orders: {timeline.lab_orders.length} · Prescriptions: {timeline.prescriptions.length}</p>
            <ul className="plain-list">
              {timeline.lab_orders.map((o) => (
                <li key={o.id}>Lab {o.order_id} · {o.status} · {o.priority}</li>
              ))}
              {timeline.prescriptions.map((p) => (
                <li key={p.id}>Rx {p.prescription_id} · {p.status}</li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <div className="muted small">{label}</div>
      <div>{value || "—"}</div>
    </div>
  );
}
