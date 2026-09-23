import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

type Tab = "timeline" | "access" | "charges" | "emergency" | "documents" | "complaints";

export function AfyaCitizenPage() {
  const [tab, setTab] = useState<Tab>("timeline");
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [complaint, setComplaint] = useState({
    category: "THAT_WASNT_ME",
    subject: "",
    description: "",
  });

  async function load(t: Tab) {
    setLoading(true);
    setError("");
    setData(null);
    try {
      const fn =
        t === "timeline"
          ? api.citizenTimeline
          : t === "access"
            ? api.citizenAccessHistory
            : t === "charges"
              ? api.citizenCharges
              : t === "emergency"
                ? api.citizenEmergency
                : t === "documents"
                  ? api.citizenDocuments
                  : api.citizenComplaints;
      const res = await fn();
      setData(res);
    } catch (e: any) {
      setError(e?.message || "Unable to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(tab);
  }, [tab]);

  async function submitComplaint(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.citizenCreateComplaint(complaint);
      setComplaint({ category: "THAT_WASNT_ME", subject: "", description: "" });
      setTab("complaints");
      await load("complaints");
    } catch (err: any) {
      setError(err?.message || "Could not submit complaint");
    }
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "timeline", label: "My Health Timeline" },
    { id: "access", label: "Who Accessed My Record" },
    { id: "charges", label: "Why Was I Charged" },
    { id: "emergency", label: "Emergency Summary" },
    { id: "documents", label: "My Documents" },
    { id: "complaints", label: "Report / That Wasn't Me" },
  ];

  return (
    <div className="page portal-page" style={{ maxWidth: 900, margin: "0 auto", padding: 16 }}>
      <p>
        <Link to="/portal">← Portal home</Link>
      </p>
      <h1>Afya Citizen</h1>
      <p className="muted">Your health, charges, privacy, and complaints — in one place.</p>

      <div className="row" style={{ flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={tab === t.id ? "btn primary" : "btn"}
            onClick={() => setTab(t.id)}
            style={{
              background: tab === t.id ? "#0b3d2e" : "#f4f4f4",
              color: tab === t.id ? "#fff" : "#111",
              border: "1px solid #ccc",
              padding: "8px 12px",
              cursor: "pointer",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading && <p>Loading…</p>}
      {error && <p style={{ color: "#a00" }}>{error}</p>}

      {!loading && tab === "timeline" && data?.events && (
        <ul className="list">
          {data.events.map((ev: any) => (
            <li key={ev.event_id} className="card" style={{ marginBottom: 8, padding: 12, border: "1px solid #ddd" }}>
              <strong>{ev.title}</strong>
              <div className="muted">{ev.event_type}</div>
              {ev.summary && <div>{ev.summary}</div>}
              {ev.occurred_at && <div className="muted">{new Date(ev.occurred_at).toLocaleString()}</div>}
            </li>
          ))}
          {!data.events.length && <p>No timeline events yet.</p>}
        </ul>
      )}

      {!loading && tab === "access" && data?.items && (
        <ul>
          {data.items.map((it: any) => (
            <li key={it.id} className="card" style={{ marginBottom: 8, padding: 12, border: "1px solid #ddd" }}>
              <strong>{it.action}</strong>
              <div className="muted">
                {it.resource_type} · {it.result}
              </div>
              {it.created_at && <div className="muted">{new Date(it.created_at).toLocaleString()}</div>}
            </li>
          ))}
          {!data.items.length && <p>No access events recorded yet.</p>}
        </ul>
      )}

      {!loading && tab === "charges" && data?.items && (
        <>
          <p>
            Total patient responsibility shown: <strong>{data.total_patient_responsibility}</strong>
          </p>
          <ul>
            {data.items.map((it: any) => (
              <li key={it.charge_or_invoice_id} className="card" style={{ marginBottom: 8, padding: 12, border: "1px solid #ddd" }}>
                <strong>
                  {it.kind}: {it.description}
                </strong>
                <div>Amount: {it.amount}</div>
                {it.explanation && <p>{it.explanation}</p>}
              </li>
            ))}
            {!data.items.length && <p>No charges found.</p>}
          </ul>
        </>
      )}

      {!loading && tab === "emergency" && data && (
        <div className="card" style={{ padding: 16, border: "1px solid #ddd" }}>
          <h2>{data.full_name}</h2>
          <p>Afya ID: {data.afya_id || "—"}</p>
          <p>
            DOB: {data.date_of_birth || "—"} · Sex: {data.sex || "—"}
          </p>
          <h3>Allergies</h3>
          <p>{(data.allergies || []).join(", ") || "None recorded"}</p>
          <h3>Medications</h3>
          <p>{(data.active_medications || []).join(", ") || "None recorded"}</p>
          <h3>Conditions</h3>
          <p>{(data.critical_conditions || []).join(", ") || "None recorded"}</p>
          <p className="muted">{data.disclaimer}</p>
        </div>
      )}

      {!loading && tab === "documents" && data?.items && (
        <ul>
          {data.items.map((d: any) => (
            <li key={d.id} className="card" style={{ marginBottom: 8, padding: 12, border: "1px solid #ddd" }}>
              <strong>{d.title}</strong>
              <div className="muted">
                {d.doc_type} · {d.status}
              </div>
            </li>
          ))}
          {!data.items.length && <p>No documents yet. Issue a continuity card from the portal.</p>}
        </ul>
      )}

      {tab === "complaints" && (
        <>
          <form onSubmit={submitComplaint} className="card" style={{ padding: 16, border: "1px solid #ddd", marginBottom: 16 }}>
            <h3>Report a problem</h3>
            <label>
              Category
              <select
                value={complaint.category}
                onChange={(e) => setComplaint({ ...complaint, category: e.target.value })}
              >
                <option value="THAT_WASNT_ME">That wasn't me</option>
                <option value="WRONG_CHARGE">Wrong charge</option>
                <option value="PRIVACY">Privacy</option>
                <option value="ACCESS">Unauthorised access</option>
                <option value="CLINICAL">Clinical concern</option>
                <option value="OTHER">Other</option>
              </select>
            </label>
            <label>
              Subject
              <input
                required
                minLength={5}
                maxLength={200}
                value={complaint.subject}
                onChange={(e) => setComplaint({ ...complaint, subject: e.target.value })}
              />
            </label>
            <label>
              Description
              <textarea
                required
                minLength={20}
                maxLength={4000}
                rows={5}
                value={complaint.description}
                onChange={(e) => setComplaint({ ...complaint, description: e.target.value })}
              />
            </label>
            <button type="submit" className="btn primary">
              Submit
            </button>
          </form>
          {!loading && data?.items && (
            <ul>
              {data.items.map((c: any) => (
                <li key={c.id} className="card" style={{ marginBottom: 8, padding: 12, border: "1px solid #ddd" }}>
                  <strong>{c.subject}</strong>
                  <div className="muted">
                    {c.category} · {c.status}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
