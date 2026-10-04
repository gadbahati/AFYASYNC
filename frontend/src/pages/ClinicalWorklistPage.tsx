/** Phase 157 — worklist with STAT/URGENT priority badges.
 *  Developed by BAHATI GAD WANGWE
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, request } from "../api/client";

type WorkItem = {
  id: string;
  order_type?: string;
  code?: string;
  description?: string;
  priority?: string;
  status?: string;
  encounter_id?: string;
  patient_id?: string;
};

function departmentLink(o: WorkItem): { path: string; label: string } | null {
  const t = (o.order_type || "").toUpperCase();
  const q = new URLSearchParams();
  if (o.patient_id) q.set("patientId", o.patient_id);
  if (o.encounter_id) q.set("encounterId", o.encounter_id);
  if (o.id) q.set("orderId", o.id);
  const qs = q.toString() ? `?${q.toString()}` : "";
  if (t === "LAB" || t === "LABORATORY") return { path: `/laboratory${qs}`, label: "Lab workbench" };
  if (t === "PHARMACY" || t === "RX") return { path: `/pharmacy${qs}`, label: "Pharmacy" };
  if (t === "IMAGING" || t === "RADIOLOGY") return { path: `/radiology${qs}`, label: "Radiology" };
  return null;
}

function PriorityBadge({ priority }: { priority?: string }) {
  const p = (priority || "ROUTINE").toUpperCase();
  if (p === "ROUTINE" || p === "NORMAL") {
    return <span className="muted small">{p}</span>;
  }
  const critical = p === "STAT" || p === "URGENT" || p === "CRITICAL" || p === "C";
  return (
    <span
      className="status-pill"
      style={{
        background: critical ? "#b91c1c" : "#b45309",
        color: "#fff",
        fontWeight: 700,
      }}
      title={critical ? "High priority — action promptly" : `Priority: ${p}`}
    >
      {p}
    </span>
  );
}

export function ClinicalWorklistPage() {
  const [params] = useSearchParams();
  const initialType = (params.get("type") || "PHARMACY").toUpperCase();
  const [orderType, setOrderType] = useState(
    ["LAB", "PHARMACY", "IMAGING", ""].includes(initialType) ? initialType : "PHARMACY",
  );
  const [data, setData] = useState<{ count?: number; order_type?: string; items?: WorkItem[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [labValue, setLabValue] = useState("");
  const [labUnits, setLabUnits] = useState("");
  const [labFlag, setLabFlag] = useState("");
  const [dispenseQty, setDispenseQty] = useState("");
  const [batchNo, setBatchNo] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const q = orderType ? `?order_type=${encodeURIComponent(orderType)}` : "";
      const body = await request(`/api/v1/clinical/worklist${q}`);
      const items: WorkItem[] = body.items || [];
      // STAT / URGENT first
      items.sort((a, b) => {
        const rank = (p?: string) => {
          const x = (p || "").toUpperCase();
          if (x === "STAT" || x === "CRITICAL" || x === "C") return 0;
          if (x === "URGENT") return 1;
          return 2;
        };
        return rank(a.priority) - rank(b.priority);
      });
      setData({ ...body, items });
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "WORKLIST_FAILED");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [orderType]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function forwardOrder(orderId: string) {
    setBusyId(orderId);
    setActionMsg(null);
    try {
      await request(`/api/v1/encounters/orders/${orderId}/forward`, { method: "POST" });
      setActionMsg(`Forwarded order ${orderId.slice(0, 8)}… to department`);
      await reload();
    } catch (err) {
      setActionMsg(err instanceof ApiError ? err.code : "FORWARD_FAILED");
    } finally {
      setBusyId(null);
    }
  }

  async function fulfillOrder(order: WorkItem) {
    setBusyId(order.id);
    setActionMsg(null);
    const t = (order.order_type || "").toUpperCase();
    const isLab = t === "LAB" || t === "LABORATORY";
    const isRx = t === "PHARMACY" || t === "RX";

    if (isLab && !labValue.trim()) {
      setActionMsg("Enter a lab result value before completing");
      setBusyId(null);
      setSelectedId(order.id);
      return;
    }
    if (isRx && !dispenseQty.trim()) {
      setActionMsg("Enter dispense quantity before completing");
      setBusyId(null);
      setSelectedId(order.id);
      return;
    }

    const body: Record<string, string> = {
      status: "COMPLETED",
      result_notes: isLab
        ? "Lab result entered from clinical worklist"
        : isRx
          ? "Pharmacy dispense from clinical worklist"
          : "Completed from clinical worklist",
    };
    if (isLab) {
      body.lab_value = labValue.trim();
      if (labUnits.trim()) body.lab_units = labUnits.trim();
      if (labFlag.trim()) body.lab_flag = labFlag.trim();
    }
    if (isRx) {
      body.dispense_qty = dispenseQty.trim();
      if (batchNo.trim()) body.batch_no = batchNo.trim();
    }

    try {
      await request(`/api/v1/encounters/orders/${order.id}/fulfill`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setActionMsg(
        isRx
          ? `Dispensed ${dispenseQty} for ${order.id.slice(0, 8)}…`
          : isLab
            ? `Lab result saved for ${order.id.slice(0, 8)}…`
            : `Fulfilled order ${order.id.slice(0, 8)}…`,
      );
      if (isLab) {
        setLabValue("");
        setLabUnits("");
        setLabFlag("");
      }
      if (isRx) {
        setDispenseQty("");
        setBatchNo("");
      }
      await reload();
    } catch (err) {
      setActionMsg(err instanceof ApiError ? err.code : "FULFILL_FAILED");
    } finally {
      setBusyId(null);
    }
  }

  const showLabForm = orderType === "LAB" || orderType === "" || orderType === "LABORATORY";
  const showRxForm = orderType === "PHARMACY" || orderType === "" || orderType === "RX";

  return (
    <div>
      <header className="page-header">
        <div>
          <Link to="/" className="muted">
            ← Dashboard
          </Link>
          <h1>Clinical worklist</h1>
          <p className="muted">STAT / URGENT sorted first · structured lab & pharmacy complete</p>
        </div>
        <div className="actions">
          <select value={orderType} onChange={(e) => setOrderType(e.target.value)} aria-label="Order type">
            <option value="PHARMACY">PHARMACY</option>
            <option value="LAB">LAB</option>
            <option value="IMAGING">IMAGING</option>
            <option value="">All types</option>
          </select>
          <button type="button" className="secondary" onClick={() => void reload()} disabled={loading}>
            Refresh
          </button>
        </div>
      </header>

      {showLabForm && (
        <section className="card" style={{ marginBottom: "1rem" }}>
          <h2>Lab result entry</h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "flex-end" }}>
            <label>
              Value{" "}
              <input value={labValue} onChange={(e) => setLabValue(e.target.value)} placeholder="e.g. 5.2" />
            </label>
            <label>
              Units{" "}
              <input value={labUnits} onChange={(e) => setLabUnits(e.target.value)} placeholder="mmol/L" />
            </label>
            <label>
              Flag{" "}
              <select value={labFlag} onChange={(e) => setLabFlag(e.target.value)}>
                <option value="">—</option>
                <option value="N">N</option>
                <option value="H">H</option>
                <option value="L">L</option>
                <option value="A">A</option>
                <option value="C">C (critical)</option>
              </select>
            </label>
          </div>
        </section>
      )}

      {showRxForm && (
        <section className="card" style={{ marginBottom: "1rem" }}>
          <h2>Pharmacy dispense</h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "flex-end" }}>
            <label>
              Quantity{" "}
              <input value={dispenseQty} onChange={(e) => setDispenseQty(e.target.value)} placeholder="e.g. 30 tablets" />
            </label>
            <label>
              Batch / lot{" "}
              <input value={batchNo} onChange={(e) => setBatchNo(e.target.value)} placeholder="optional" />
            </label>
          </div>
        </section>
      )}

      {loading && <p>Loading worklist…</p>}
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {actionMsg && (
        <p className="muted" role="status">
          {actionMsg}
        </p>
      )}

      {data && (
        <section className="card">
          <h2>
            Queue ({data.count ?? 0}) · {data.order_type || orderType || "ALL"}
          </h2>
          <ul className="plain-list">
            {(data.items || []).map((o) => {
              const dept = departmentLink(o);
              const selected = selectedId === o.id;
              const high =
                ["STAT", "URGENT", "CRITICAL", "C"].includes((o.priority || "").toUpperCase());
              return (
                <li
                  key={o.id}
                  style={{
                    marginBottom: "0.75rem",
                    padding: "0.5rem",
                    border: selected || high ? "1px solid" : undefined,
                    borderColor: high ? "#b91c1c" : selected ? "var(--border, #ccc)" : undefined,
                    borderRadius: "6px",
                    cursor: "pointer",
                    background: high ? "rgba(185, 28, 28, 0.06)" : undefined,
                  }}
                  onClick={() => setSelectedId(o.id)}
                >
                  <div>
                    <strong>{o.order_type}</strong> {o.code || ""} — {o.description} ·{" "}
                    <PriorityBadge priority={o.priority} /> ·{" "}
                    <span className="status-pill">{o.status}</span>
                    {selected && <span className="muted small"> · selected</span>}
                  </div>
                  <div className="actions" style={{ marginTop: "0.35rem", flexWrap: "wrap", gap: "0.35rem" }}>
                    {o.patient_id && (
                      <Link
                        className="button secondary"
                        to={`/patients/${o.patient_id}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        Patient
                      </Link>
                    )}
                    {o.encounter_id && (
                      <Link
                        className="button secondary"
                        to={`/encounters/${o.encounter_id}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        Encounter
                      </Link>
                    )}
                    {dept && (
                      <Link className="button secondary" to={dept.path} onClick={(e) => e.stopPropagation()}>
                        {dept.label}
                      </Link>
                    )}
                    {(o.status === "ORDERED" || o.status === "IN_PROGRESS") && (
                      <>
                        <button
                          type="button"
                          className="secondary"
                          disabled={busyId === o.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            void forwardOrder(o.id);
                          }}
                        >
                          Forward to dept
                        </button>
                        <button
                          type="button"
                          disabled={busyId === o.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedId(o.id);
                            void fulfillOrder(o);
                          }}
                        >
                          Mark complete
                        </button>
                      </>
                    )}
                  </div>
                </li>
              );
            })}
            {(data.items || []).length === 0 && <li className="muted">No open orders in this queue.</li>}
          </ul>
          <p className="muted small">Developed by BAHATI GAD WANGWE · Phase 157</p>
        </section>
      )}
    </div>
  );
}
