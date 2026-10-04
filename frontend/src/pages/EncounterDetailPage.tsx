import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { ClinicalTimeline, Triage } from "../api/types";
import { EncounterOrdersPanel } from "./EncounterOrdersPanel";
import { EncounterDischargePanel } from "./EncounterDischargePanel";

export function EncounterDetailPage() {
  const { encounterId } = useParams();
  const [timeline, setTimeline] = useState<ClinicalTimeline | null>(null);
  const [triage, setTriage] = useState<Triage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    if (!encounterId) return;
    const [data, latestTriage] = await Promise.all([api.getClinicalTimeline(encounterId), api.getLatestTriage(encounterId)]);
    setTimeline(data);
    setTriage(latestTriage);
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

  async function onTriage(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!encounterId) return;
    const fd = new FormData(e.currentTarget);
    const redFlags = String(fd.get("red_flags") || "").split(",").map((v) => v.trim()).filter(Boolean);
    setBusy(true);
    setError(null);
    try {
      const saved = await api.recordTriage(encounterId, {
        acuity: Number(fd.get("acuity")),
        chief_complaint: String(fd.get("chief_complaint") || "").trim() || null,
        red_flags: redFlags,
        disposition: String(fd.get("disposition") || "").trim() || null,
        notes: String(fd.get("notes") || "").trim() || null,
      });
      setTriage(saved);
      e.currentTarget.reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "TRIAGE_FAILED");
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
      const status = String(fd.get("status") || "DRAFT");
      if (status === "FINAL" && !text("assessment")) { setError("ASSESSMENT_REQUIRED_FOR_FINAL"); return; }
      if (status === "FINAL" && !text("treatment_plan")) { setError("TREATMENT_PLAN_REQUIRED_FOR_FINAL"); return; }
      await api.saveConsultation(encounterId, {
        chief_complaint: text("chief_complaint"),
        history: text("history"),
        examination: text("examination"),
        assessment: text("assessment"),
        clinical_notes: text("clinical_notes"),
        treatment_plan: text("treatment_plan"),
        status,
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
            <h2>Triage & acuity</h2>
            {triage ? (
              <div className="detail-grid">
                <Field label="Acuity" value={`Level ${triage.acuity} · ${triage.priority}`} />
                <Field label="Chief complaint" value={triage.chief_complaint} />
                <Field label="Red flags" value={triage.red_flags.length ? triage.red_flags.join(", ") : "None recorded"} />
                <Field label="Disposition" value={triage.disposition} />
                <Field label="Notes" value={triage.notes} />
                <Field label="Assessed" value={new Date(triage.assessed_at).toLocaleString()} />
              </div>
            ) : (
              <p className="muted">No triage assessment recorded yet.</p>
            )}
            {open && (
              <form className="form-grid" onSubmit={onTriage}>
                <label>Acuity<select name="acuity" defaultValue={triage?.acuity || 3}>
                  <option value="1">1 — Resuscitation / immediate</option>
                  <option value="2">2 — Emergency / very urgent</option>
                  <option value="3">3 — Urgent</option>
                  <option value="4">4 — Less urgent</option>
                  <option value="5">5 — Non-urgent</option>
                </select></label>
                <label className="full">Chief complaint <input name="chief_complaint" defaultValue={triage?.chief_complaint || ""} maxLength={5000} /></label>
                <label className="full">Red flags <input name="red_flags" placeholder="e.g. chest pain, severe bleeding, altered consciousness" /></label>
                <label>Disposition<select name="disposition" defaultValue={triage?.disposition || ""}>
                  <option value="">Select</option><option value="IMMEDIATE_CARE">Immediate care</option><option value="URGENT_REVIEW">Urgent review</option><option value="ROUTINE_REVIEW">Routine review</option><option value="OBSERVATION">Observation</option><option value="REFERRAL">Referral</option>
                </select></label>
                <label className="full">Triage notes <textarea name="notes" rows={2} defaultValue={triage?.notes || ""} maxLength={10000} /></label>
                <div className="full actions"><button type="submit" disabled={busy}>Save triage assessment</button></div>
              </form>
            )}
          </section>

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
                <label>Status<select name="status" defaultValue={timeline.consultation?.status || "DRAFT"} disabled={timeline.consultation?.status === "FINAL"}><option value="DRAFT">Draft</option><option value="FINAL">Final / sign</option></select></label>
                <div className="full actions">
                  <button type="submit" disabled={busy || timeline.consultation?.status === "FINAL"}>{timeline.consultation?.status === "FINAL" ? "Consultation signed" : "Save consultation"}</button>
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
            <h2>Procedures</h2>
            {timeline.procedures.length === 0 && <p className="muted">No procedures recorded.</p>}
            <ul className="plain-list">
              {timeline.procedures.map((p) => (
                <li key={p.id}>{p.procedure_name}{p.procedure_code ? ` (${p.procedure_code})` : ""} · {p.status} · {new Date(p.performed_at).toLocaleString()}</li>
              ))}
            </ul>
            {open && (
              <form className="form-grid" onSubmit={async (e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget);
                setBusy(true); setError(null);
                try {
                  await api.addProcedure(encounterId!, {
                    procedure_name: String(fd.get("procedure_name") || "").trim(),
                    procedure_code: String(fd.get("procedure_code") || "").trim() || null,
                    procedure_type: String(fd.get("procedure_type") || "CLINICAL"),
                    status: String(fd.get("procedure_status") || "COMPLETED"),
                    outcome: String(fd.get("outcome") || "").trim() || null,
                    notes: String(fd.get("procedure_notes") || "").trim() || null,
                  });
                  e.currentTarget.reset(); await reload();
                } catch (err) { setError(err instanceof ApiError ? err.code : "PROCEDURE_FAILED"); }
                finally { setBusy(false); }
              }}>
                <label>Name <input name="procedure_name" required /></label>
                <label>Code <input name="procedure_code" /></label>
                <label>Type <input name="procedure_type" defaultValue="CLINICAL" /></label>
                <label>Status<select name="procedure_status"><option value="COMPLETED">Completed</option><option value="PLANNED">Planned</option><option value="IN_PROGRESS">In progress</option><option value="CANCELLED">Cancelled</option></select></label>
                <label className="full">Outcome <textarea name="outcome" rows={2} /></label>
                <label className="full">Procedure notes <textarea name="procedure_notes" rows={2} /></label>
                <div className="full actions"><button type="submit" disabled={busy}>Record procedure</button></div>
              </form>
            )}
          </section>

          <section className="card">
            <h2>Clinical notes</h2>
            {timeline.clinical_notes.length === 0 && <p className="muted">No clinical notes recorded.</p>}
            <ul className="plain-list">
              {timeline.clinical_notes.map((n) => (
                <li key={n.id}><strong>{n.note_type}</strong> · {n.status} · {n.content} · {new Date(n.created_at).toLocaleString()}</li>
              ))}
            </ul>
            {open && (
              <form className="form-grid" onSubmit={async (e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget);
                setBusy(true); setError(null);
                try {
                  await api.addClinicalNote(encounterId!, {
                    note_type: String(fd.get("note_type") || "PROGRESS"),
                    content: String(fd.get("content") || "").trim(),
                    status: String(fd.get("note_status") || "DRAFT"),
                  });
                  e.currentTarget.reset(); await reload();
                } catch (err) { setError(err instanceof ApiError ? err.code : "CLINICAL_NOTE_FAILED"); }
                finally { setBusy(false); }
              }}>
                <label>Type<select name="note_type"><option value="PROGRESS">Progress</option><option value="NURSING">Nursing</option><option value="SPECIALIST">Specialist</option><option value="DISCHARGE">Discharge</option><option value="REFERRAL">Referral</option><option value="OTHER">Other</option></select></label>
                <label>Status<select name="note_status"><option value="DRAFT">Draft</option><option value="FINAL">Final / sign</option></select></label>
                <label className="full">Note <textarea name="content" rows={4} required maxLength={20000} /></label>
                <div className="full actions"><button type="submit" disabled={busy}>Save clinical note</button></div>
              </form>
            )}
          </section>

          <EncounterOrdersPanel
            encounterId={encounterId!}
            open={!!open}
            legacyLabCount={timeline.lab_orders?.length ?? 0}
            legacyRxCount={timeline.prescriptions?.length ?? 0}
          />
          <EncounterDischargePanel
            encounterId={encounterId!}
            open={!!open}
            onDischarged={() => void reload()}
          />
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
