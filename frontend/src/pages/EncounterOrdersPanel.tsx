/** Phase 134 — place, forward, and fulfill clinical orders. Developed by BAHATI GAD WANGWE */
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";

type Props = {
  encounterId: string;
  open: boolean;
  legacyLabCount?: number;
  legacyRxCount?: number;
};

export function EncounterOrdersPanel({ encounterId, open, legacyLabCount = 0, legacyRxCount = 0 }: Props) {
  const [orders, setOrders] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const rows = await api.listClinicalOrders(encounterId).catch(() => []);
    setOrders(Array.isArray(rows) ? rows : []);
  }, [encounterId]);

  useEffect(() => {
    void reload().catch(() => setOrders([]));
  }, [reload]);

  return (
    <section className="card">
      <h2>Clinical orders</h2>
      <p className="muted small">
        Phase 132–134 · LAB / PHARMACY / IMAGING · Legacy lab: {legacyLabCount} · Rx: {legacyRxCount}
      </p>
      {error && <div className="error">{error}</div>}
      {open && (
        <form
          className="form-grid"
          onSubmit={async (e) => {
            e.preventDefault();
            const fd = new FormData(e.currentTarget);
            setBusy(true);
            setError(null);
            try {
              await api.createClinicalOrder(encounterId, {
                order_type: String(fd.get("order_type") || "LAB"),
                code: String(fd.get("code") || "") || undefined,
                description: String(fd.get("description") || ""),
                priority: String(fd.get("priority") || "ROUTINE"),
                notes: String(fd.get("notes") || "") || undefined,
              });
              e.currentTarget.reset();
              await reload();
            } catch (err) {
              setError(err instanceof ApiError ? err.code : "ORDER_FAILED");
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            Type
            <select name="order_type" defaultValue="LAB">
              <option value="LAB">LAB</option>
              <option value="PHARMACY">PHARMACY</option>
              <option value="IMAGING">IMAGING</option>
            </select>
          </label>
          <label>
            Priority
            <select name="priority" defaultValue="ROUTINE">
              <option value="ROUTINE">ROUTINE</option>
              <option value="URGENT">URGENT</option>
              <option value="STAT">STAT</option>
            </select>
          </label>
          <label>
            Code
            <input name="code" placeholder="e.g. CBC or drug code" />
          </label>
          <label className="span-2">
            Description
            <input name="description" required placeholder="What to order" />
          </label>
          <label className="span-2">
            Notes
            <input name="notes" placeholder="Optional" />
          </label>
          <div className="form-actions span-2">
            <button type="submit" disabled={busy}>
              Place order
            </button>
          </div>
        </form>
      )}
      <ul className="plain-list" style={{ marginTop: "1rem" }}>
        {orders.map((o) => (
          <li key={o.id} style={{ marginBottom: "0.5rem" }}>
            <strong>{o.order_type}</strong> {o.code || ""} — {o.description} · {o.priority} ·{" "}
            <span className="status-pill">{o.status}</span>
            {o.notes && <div className="muted small">{o.notes}</div>}
            {["ORDERED", "IN_PROGRESS"].includes(o.status) && (
              <div className="actions" style={{ marginTop: 4 }}>
                <button
                  type="button"
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    void (async () => {
                      setBusy(true);
                      try {
                        await api.fulfillClinicalOrder(o.id, { status: "IN_PROGRESS" });
                        await reload();
                      } catch (err) {
                        setError(err instanceof ApiError ? err.code : "FULFILL_FAILED");
                      } finally {
                        setBusy(false);
                      }
                    })()
                  }
                >
                  Start
                </button>
                <button
                  type="button"
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    void (async () => {
                      setBusy(true);
                      setError(null);
                      try {
                        const res = await api.forwardClinicalOrder(o.id);
                        const msg = res?.forward?.message || "Forwarded";
                        if (res?.forward && res.forward.matched === false) {
                          setError(msg);
                        }
                        await reload();
                      } catch (err) {
                        setError(err instanceof ApiError ? err.code : "FORWARD_FAILED");
                      } finally {
                        setBusy(false);
                      }
                    })()
                  }
                >
                  Forward to dept
                </button>
                <button
                  type="button"
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    void (async () => {
                      const result_notes = window.prompt("Result notes (optional):") || undefined;
                      setBusy(true);
                      try {
                        await api.fulfillClinicalOrder(o.id, { status: "COMPLETED", result_notes });
                        await reload();
                      } catch (err) {
                        setError(err instanceof ApiError ? err.code : "FULFILL_FAILED");
                      } finally {
                        setBusy(false);
                      }
                    })()
                  }
                >
                  Complete
                </button>
                <button
                  type="button"
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    void (async () => {
                      setBusy(true);
                      try {
                        await api.fulfillClinicalOrder(o.id, {
                          status: "CANCELLED",
                          result_notes: "Cancelled by clinician",
                        });
                        await reload();
                      } catch (err) {
                        setError(err instanceof ApiError ? err.code : "CANCEL_FAILED");
                      } finally {
                        setBusy(false);
                      }
                    })()
                  }
                >
                  Cancel
                </button>
              </div>
            )}
          </li>
        ))}
        {orders.length === 0 && <li className="muted">No clinical orders yet.</li>}
      </ul>
      <p className="muted small">Developed by BAHATI GAD WANGWE · Phase 134</p>
    </section>
  );
}
