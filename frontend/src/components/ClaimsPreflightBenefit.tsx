/** Phase 108 — show benefit-engine + preauth counters on claims preflight.
 *  Developed by BAHATI GAD WANGWE
 */

type Props = {
  benefit_engine_payer_total?: number;
  benefit_engine_patient_total?: number;
  benefit_preauth_lines?: number;
  benefit_unknown_rules?: number;
  benefit_ineligible_lines?: number;
  errors?: string[];
  warnings?: string[];
  money: (n: number | string) => string;
};

export function ClaimsPreflightBenefit({
  benefit_engine_payer_total,
  benefit_engine_patient_total,
  benefit_preauth_lines,
  benefit_unknown_rules,
  benefit_ineligible_lines,
  errors = [],
  warnings = [],
  money,
}: Props) {
  const preauthErrors = errors.filter((e) => e.startsWith("PREAUTH_") || e.startsWith("BENEFIT_EXCLUDED"));
  const preauthWarns = warnings.filter(
    (w) => w.startsWith("PREAUTH_") || w.startsWith("BENEFIT_PREAUTH") || w.startsWith("BENEFIT_RULE"),
  );
  const hasEngine =
    benefit_engine_payer_total != null ||
    benefit_preauth_lines != null ||
    benefit_unknown_rules != null;

  if (!hasEngine && preauthErrors.length === 0 && preauthWarns.length === 0) return null;

  return (
    <div style={{ marginTop: "0.5rem" }}>
      {hasEngine && (
        <p className="small muted" style={{ margin: "0.35rem 0 0" }}>
          Benefit engine · payer {money(benefit_engine_payer_total ?? 0)} · patient{" "}
          {money(benefit_engine_patient_total ?? 0)}
          {benefit_preauth_lines ? ` · preauth lines ${benefit_preauth_lines}` : ""}
          {benefit_unknown_rules ? ` · missing rules ${benefit_unknown_rules}` : ""}
          {benefit_ineligible_lines ? ` · excluded ${benefit_ineligible_lines}` : ""}
        </p>
      )}
      {preauthErrors.length > 0 && (
        <ul className="small" style={{ marginTop: "0.35rem", color: "#b91c1c" }}>
          {preauthErrors.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}
      {preauthWarns.length > 0 && (
        <ul className="small muted" style={{ marginTop: "0.25rem" }}>
          {preauthWarns.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
