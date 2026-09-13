import { useEffect, useState, type FormEvent } from "react";
import { coverageApi, type Payer, type PayerPlan } from "../api/coverage";

type Props = {
  personId: string;
  onAttached: () => void;
};

export function AttachCoverageForm({ personId, onAttached }: Props) {
  const [payers, setPayers] = useState<Payer[]>([]);
  const [plans, setPlans] = useState<PayerPlan[]>([]);
  const [payerId, setPayerId] = useState("");
  const [planId, setPlanId] = useState("");
  const [membership, setMembership] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    coverageApi
      .listPayers()
      .then((list) => {
        setPayers(list);
        if (list[0]) setPayerId(list[0].id);
      })
      .catch(() => setError("Unable to load payers"));
  }, []);

  useEffect(() => {
    if (!payerId) return;
    coverageApi
      .listPlans(payerId)
      .then((list) => {
        setPlans(list);
        setPlanId(list[0]?.id || "");
      })
      .catch(() => setPlans([]));
  }, [payerId]);

  const selected = payers.find((p) => p.id === payerId);
  const needsMembership = selected && selected.code !== "CASH";

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (needsMembership && !membership.trim()) {
      setError(selected?.code === "SHA" ? "Enter SHA membership / member number" : "Enter membership number");
      return;
    }
    setBusy(true);
    try {
      await coverageApi.attach({
        person_id: personId,
        payer_id: payerId,
        payer_plan_id: planId || null,
        membership_number: membership.trim() || null,
      });
      setMembership("");
      setOpen(false);
      onAttached();
    } catch (err) {
      setError(err instanceof Error ? err.message : "ATTACH_FAILED");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button type="button" className="button secondary" onClick={() => setOpen(true)}>
        Attach coverage
      </button>
    );
  }

  return (
    <form className="card form-grid" onSubmit={onSubmit} style={{ marginTop: 12 }}>
      <p className="muted full">
        Attach AfyaSync membership, SHA cover (no AfyaSync membership required), or mark cash/self-pay.
      </p>
      <label>
        Payer
        <select required value={payerId} onChange={(e) => setPayerId(e.target.value)}>
          {payers.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} ({p.code})
            </option>
          ))}
        </select>
      </label>
      <label>
        Plan
        <select value={planId} onChange={(e) => setPlanId(e.target.value)}>
          {plans.length === 0 && <option value="">No plan</option>}
          {plans.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </label>
      {needsMembership && (
        <label className="full">
          {selected?.code === "SHA" ? "SHA membership number" : "Membership number"}
          <input
            value={membership}
            onChange={(e) => setMembership(e.target.value)}
            placeholder={selected?.code === "SHA" ? "SHA / SHIF member number" : "AfyaSync membership number"}
          />
        </label>
      )}
      {error && <div className="error full">{error}</div>}
      <div className="full actions">
        <button type="submit" disabled={busy}>{busy ? "Saving…" : "Save coverage"}</button>
        <button type="button" className="button secondary" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  );
}
