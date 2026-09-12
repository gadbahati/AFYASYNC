import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Patient } from "../api/types";

export function PatientDetailPage() {
  const { patientId } = useParams();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;
    api
      .getPatient(patientId)
      .then((data) => {
        if (!cancelled) setPatient(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.code : "PATIENT_LOAD_FAILED");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  return (
    <div>
      <header className="page-header">
        <div>
          <Link to="/patients" className="muted">← Patients</Link>
          <h1>Patient record</h1>
        </div>
      </header>

      {loading && <p>Loading…</p>}
      {error && <div className="error">{error}</div>}

      {patient && (
        <div className="card detail-grid">
          <Field label="Afya ID" value={patient.afya_id} />
          <Field label="Name" value={[patient.first_name, patient.middle_name, patient.last_name].filter(Boolean).join(" ")} />
          <Field label="Date of birth" value={patient.date_of_birth || "—"} />
          <Field label="Sex" value={patient.sex || "—"} />
          <Field label="Phone" value={patient.phone || "—"} />
          <Field label="Email" value={patient.email || "—"} />
          <Field label="Address" value={patient.address || "—"} />
          <Field label="Status" value={patient.status} />
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="muted small">{label}</div>
      <div>{value}</div>
    </div>
  );
}
