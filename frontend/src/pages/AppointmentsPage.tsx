import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Appointment, Department, Patient } from "../api/types";

type IncomingRequest = {
  id: string;
  patient_id: string;
  status: string;
  reason: string;
  preferred_date?: string | null;
  patient_notes?: string | null;
  created_at: string;
};

export function AppointmentsPage() {
  const [params] = useSearchParams();
  const [rows, setRows] = useState<Appointment[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [incoming, setIncoming] = useState<IncomingRequest[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [respondingId, setRespondingId] = useState<string | null>(null);
  const [offerDate, setOfferDate] = useState("");
  const [responseNotes, setResponseNotes] = useState("");
  const [form, setForm] = useState({
    patient_id: params.get("patientId") || "",
    department_id: "",
    provider_id: "",
    date: "",
    reason: "Doctor follow-up",
  });

  async function load() {
    setLoading(true);
    try {
      const [a, p, d, reqs] = await Promise.all([
        api.listAppointments(),
        api.listPatients(200, 0),
        api.listDepartments(""),
        api.facilityAppointmentRequests("PENDING").catch(() => []),
      ]);
      setRows(a);
      setPatients(p.items);
      setDepartments(d);
      setIncoming(Array.isArray(reqs) ? reqs : []);
    } catch (e) {
      setError(e instanceof ApiError ? e.code : "LOAD_FAILED");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function book() {
    if (!form.patient_id || !form.department_id || !form.date) {
      setNotice("Select patient, department and return date/time.");
      return;
    }
    setSaving(true);
    try {
      const a = await api.createAppointment({
        patient_id: form.patient_id,
        department_id: form.department_id,
        provider_id: form.provider_id || null,
        appointment_at: new Date(form.date).toISOString(),
        reason: form.reason,
      });
      setRows((c) => [...c, a]);
      setNotice("Appointment booked.");
    } catch (e) {
      setNotice(e instanceof ApiError ? e.code : "BOOKING_FAILED");
    } finally {
      setSaving(false);
    }
  }

  async function respond(requestId: string, decision: "ACCEPTED" | "DECLINED" | "RESCHEDULED") {
    if ((decision === "ACCEPTED" || decision === "RESCHEDULED") && !offerDate) {
      setNotice("Set an offered date/time before accepting or rescheduling.");
      return;
    }
    setSaving(true);
    setNotice(null);
    try {
      await api.facilityRespondAppointment(requestId, {
        decision,
        offered_appointment_at: offerDate ? new Date(offerDate).toISOString() : null,
        response_notes: responseNotes || null,
        department_id: form.department_id || null,
      });
      setNotice(`Request ${decision.toLowerCase()}.`);
      setRespondingId(null);
      setOfferDate("");
      setResponseNotes("");
      await load();
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message || e.code : "RESPONSE_FAILED");
    } finally {
      setSaving(false);
    }
  }

  const name = (id: string) => {
    const p = patients.find((x) => x.id === id);
    return p ? [p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ") : id;
  };

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Continuity of care</p>
          <h1>Appointments & return visits</h1>
          <p className="muted">
            Schedule patients and respond to portal booking requests from patients.
          </p>
        </div>
      </header>

      {error && <div className="error">{error}</div>}
      {notice && <div className="success-box">{notice}</div>}

      <article className="card">
        <h2>Incoming patient requests</h2>
        <p className="muted small">
          Patients book from the AfyaSync portal. Accept with a date, propose another time, or
          decline.
        </p>
        {incoming.length === 0 ? (
          <p className="muted small">No pending requests.</p>
        ) : (
          <div className="stack">
            {incoming.map((r) => (
              <div key={r.id} className="notice">
                <div className="row-between">
                  <strong>{name(r.patient_id)}</strong>
                  <span className="status-pill">{r.status}</span>
                </div>
                <p className="small">{r.reason}</p>
                {r.preferred_date && (
                  <p className="muted small">
                    Preferred: {new Date(r.preferred_date).toLocaleString()}
                  </p>
                )}
                {r.patient_notes && <p className="muted small">Note: {r.patient_notes}</p>}
                {respondingId === r.id ? (
                  <div className="form-grid" style={{ marginTop: 10 }}>
                    <label>
                      Offered date & time
                      <input
                        type="datetime-local"
                        value={offerDate}
                        onChange={(e) => setOfferDate(e.target.value)}
                      />
                    </label>
                    <label>
                      Department (optional)
                      <select
                        value={form.department_id}
                        onChange={(e) => setForm({ ...form, department_id: e.target.value })}
                      >
                        <option value="">Any / first available</option>
                        {departments.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="span-2">
                      Message to patient
                      <input
                        value={responseNotes}
                        onChange={(e) => setResponseNotes(e.target.value)}
                        placeholder="Optional note"
                      />
                    </label>
                    <div className="form-actions span-2">
                      <button
                        type="button"
                        disabled={saving}
                        onClick={() => void respond(r.id, "ACCEPTED")}
                      >
                        Accept
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        disabled={saving}
                        onClick={() => void respond(r.id, "RESCHEDULED")}
                      >
                        Propose time
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        disabled={saving}
                        onClick={() => void respond(r.id, "DECLINED")}
                      >
                        Decline
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => setRespondingId(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="form-actions" style={{ marginTop: 8 }}>
                    <button type="button" onClick={() => setRespondingId(r.id)}>
                      Respond
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </article>

      <article className="card">
        <h2>Book a future visit</h2>
        <div className="form-grid">
          <label>
            Patient
            <select
              value={form.patient_id}
              onChange={(e) => setForm({ ...form, patient_id: e.target.value })}
            >
              <option value="">Select patient</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {[p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ")} ·{" "}
                  {p.afya_id}
                </option>
              ))}
            </select>
          </label>
          <label>
            Department
            <select
              value={form.department_id}
              onChange={(e) => setForm({ ...form, department_id: e.target.value })}
            >
              <option value="">Select department</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Provider (optional)
            <input
              value={form.provider_id}
              onChange={(e) => setForm({ ...form, provider_id: e.target.value })}
            />
          </label>
          <label>
            Return date & time
            <input
              type="datetime-local"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
            />
          </label>
          <label className="span-2">
            Reason
            <input
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
            />
          </label>
        </div>
        <div className="form-actions">
          <button onClick={() => void book()} disabled={saving}>
            {saving ? "Booking…" : "Book appointment"}
          </button>
        </div>
      </article>

      {loading ? (
        <p>Loading…</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date & time</th>
                <th>Patient</th>
                <th>Department</th>
                <th>Doctor</th>
                <th>Reason</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id}>
                  <td>{new Date(a.appointment_at).toLocaleString()}</td>
                  <td>
                    <Link to={`/patients/${a.patient_id}/journey`}>
                      <strong>{name(a.patient_id)}</strong>
                    </Link>
                  </td>
                  <td>
                    {departments.find((d) => d.id === a.department_id)?.name || a.department_id}
                  </td>
                  <td>{a.provider_id || "Any available doctor"}</td>
                  <td>{a.reason || "Return visit"}</td>
                  <td>
                    <span className="status-pill">{a.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
