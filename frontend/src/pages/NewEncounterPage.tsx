import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Department, Patient } from "../api/types";
import { useAuth } from "../auth/AuthContext";

 cons COVERAGE_OPTIONS = [
  {
    value: "CASH",
    label: "Cash / uninsured",
    help: "Patient pays at facility. No AfyaSync membership or SHA claim required.",
  },
  {
    value: "AFYASYNC",
    label: "AfyaSync membership",
    help: "Standalone AfyaSync cover. Patient can register on AfyaSync without SHA.",
  },
  {
    value: "SHA",
    label: "SHA member",
    help: "Accept SHA without forcing AfyaSync membership. Facility record still runs on AfyaSync.",
  },
  {
    value: "OTHER",
    label: "Other payer",
    help: "Corporate or other third-party cover.",
  },
] as const;

export function NewEncounterPage() {
  const { patientId } = useParams();
  const auth = useAuth();
  const navigate = useNavigate();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [departmentId, setDepartmentId] = useState("");
  const [encounterType, setEncounterType] = useState("OUTPATIENT");
  const [coverageMode, setCoverageMode] = useState<"AFYASYNC" | "SHA" | "CASH" | "OTHER">("CASH");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!patientId || !auth.facilityId) return;
    let cancelled = false;
    Promise.all([api.getPatient(patientId), api.listDepartments(auth.facilityId)])
      .then(([p, deps]) => {
        if (cancelled) return;
        setPatient(p);
        const active = deps.filter((d) => d.status === "ACTIVE");
        setDepartments(active);
        if (active[0]) setDepartmentId(active[0].id);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.code : "LOAD_FAILED");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [patientId, auth.facilityId]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!patientId || !auth.facilityId) return;
    setError(null);
    setSubmitting(true);
    try {
      const encounter = await api.createEncounter({
        patient_id: patientId,
        facility_id: auth.facilityId,
        department_id: departmentId,
        encounter_type: encounterType,
        coverage_mode: coverageMode,
        reason: reason.trim() || null,
      });
      navigate(`/encounters/${encounter.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "CREATE_FAILED");
    } finally {
      setSubmitting(false);
    }
  }

  const selectedHelp = COVERAGE_OPTIONS.find((o) => o.value === coverageMode)?.help;

  return (
    <div>
      <header className="page-header">
        <div>
          <Link to={patientId ? `/patients/${patientId}` : "/patients"} className="muted">← Patient</Link>
          <h1>Open encounter</h1>
          <p className="muted">
            {patient
              ? `${patient.afya_id} · ${[patient.first_name, patient.last_name].join(" ")}`
              : "Facility-scoped clinical visit"}
          </p>
        </div>
      </header>

      {loading && <p>Loading…</p>}
      {error && <div className="error">{error}</div>}

      {!loading && patient && (
        <form className="card form-grid" onSubmit={onSubmit}>
          <label>
            Department
            <select required value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
              ))}
            </select>
          </label>
          <label>
            Encounter type
            <select value={encounterType} onChange={(e) => setEncounterType(e.target.value)}>
              <option value="OUTPATIENT">Outpatient</option>
              <option value="INPATIENT">Inpatient</option>
              <option value="EMERGENCY">Emergency</option>
              <option value="FOLLOW_UP">Follow-up</option>
            </select>
          </label>
          <label className="full">
            Coverage for this visit
            <select
              required
              value={coverageMode}
              onChange={(e) => setCoverageMode(e.target.value as typeof coverageMode)}
            >
              {COVERAGE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          {selectedHelp && <p className="muted full">{selectedHelp}</p>}
          <label className="full">
            Reason
            <input value={reason} onChange={(e) => setReason(e.target.value)} maxLength={2000} />
          </label>
          <div className="full actions">
            <button type="submit" disabled={submitting || !departmentId}>
              {submitting ? "Opening…" : "Open encounter"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
