import type { ReactNode } from "react";
import { SCENARIOS, type ScenarioKey } from "../../adapters/mockAdapter.ts";
import { CANDIDATE_LABEL } from "../../lib/decision.ts";
import type { FieldErrors, FieldName, FormValues } from "../../lib/form.ts";
import { formatDate, SUPPORTED_CURRENCIES } from "../../lib/money.ts";
import { isBeforeDay } from "../../lib/today.ts";
import { CANDIDATE_TYPES } from "../../types/api.ts";

interface Props {
  readonly values: FormValues;
  readonly errors: FieldErrors;
  readonly busy: boolean;
  /** Mock scenario control; only shown in mock mode. */
  readonly showMockControls: boolean;
  /** Today's local date in live mode (null in mock mode); used only to flag an earlier analysis date. */
  readonly today: string | null;
  readonly scenario: ScenarioKey;
  readonly onScenario: (key: ScenarioKey) => void;
  readonly onChange: (patch: Partial<FormValues>) => void;
  readonly onSubmit: () => void;
  readonly onSample: () => void;
  readonly onClear: () => void;
  readonly onFocusField: (field: FieldName) => void;
}

const LABELS: Readonly<Record<FieldName, string>> = {
  asOf: "Analysis date",
  homeCurrency: "Home currency",
  balance: "Current available balance",
  balanceAsOf: "Balance as of",
  reserve: "Minimum balance to keep",
  purchaseAmount: "Purchase amount",
  purchaseCurrency: "Purchase currency",
  desiredBy: "Wanted by",
  methods: "Payment approaches",
  maxInstallmentDays: "Longest installment term (days)",
};

interface FieldProps {
  readonly name: FieldName;
  readonly hint?: string;
  readonly error: string | undefined;
  readonly optional?: boolean;
  readonly children: (a: { id: string; describedBy: string | undefined; invalid: boolean }) => ReactNode;
}

function Field({ name, hint, error, optional, children }: FieldProps) {
  const id = `field-${name}`;
  const ids = [hint ? `${id}-hint` : null, error ? `${id}-err` : null].filter((x): x is string => x !== null);
  return (
    <div className={error ? "field field--error" : "field"}>
      <label htmlFor={id}>
        {LABELS[name]}
        {optional && <span className="optional"> (optional)</span>}
      </label>
      {children({ id, describedBy: ids.length > 0 ? ids.join(" ") : undefined, invalid: error !== undefined })}
      {hint && (
        <p id={`${id}-hint`} className="hint">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-err`} className="error-text">
          <span aria-hidden="true">⚠ </span>
          {error}
        </p>
      )}
    </div>
  );
}

export function BuyOrWaitForm(p: Props) {
  const { values: v, errors: e, onChange } = p;
  const errorList = (Object.keys(e) as FieldName[]).filter((k) => e[k] !== undefined);
  const text = (name: FieldName, key: keyof FormValues, props?: { hint?: string; optional?: boolean; inputMode?: "decimal" | "numeric"; type?: "date"; placeholder?: string }) => (
    <Field name={name} hint={props?.hint} optional={props?.optional} error={e[name]}>
      {({ id, describedBy, invalid }) => (
        <input
          id={id}
          type={props?.type ?? "text"}
          inputMode={props?.inputMode}
          autoComplete="off"
          spellCheck={false}
          placeholder={props?.placeholder}
          value={String(v[key])}
          aria-invalid={invalid}
          aria-describedby={describedBy}
          onChange={(ev) => onChange({ [key]: ev.target.value } as Partial<FormValues>)}
        />
      )}
    </Field>
  );
  const asOfHint =
    p.today !== null && /^\d{4}-\d{2}-\d{2}$/.test(v.asOf) && isBeforeDay(v.asOf, p.today)
      ? `This is earlier than today (${formatDate(p.today)}). The engine uses exactly the date you give; change it unless this is a deliberate what-if.`
      : p.today !== null
        ? "Defaults to today's date on this computer. The engine never reads a clock; the date is sent with the request."
        : "The engine never reads a clock; the date is supplied with the request.";
  const currency = (name: "homeCurrency" | "purchaseCurrency") => (
    <Field name={name} error={e[name]}>
      {({ id, describedBy, invalid }) => (
        <select id={id} value={v[name]} aria-invalid={invalid} aria-describedby={describedBy} onChange={(ev) => onChange({ [name]: ev.target.value } as Partial<FormValues>)}>
          {SUPPORTED_CURRENCIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      )}
    </Field>
  );

  return (
    <form
      className="form"
      noValidate
      aria-labelledby="form-h"
      onSubmit={(ev) => {
        ev.preventDefault();
        p.onSubmit();
      }}
    >
      <h1 id="form-h">Buy or wait?</h1>
      <p className="lede">Enter the purchase and your position. The engine, not this screen, returns the outcome.</p>

      {errorList.length > 0 && (
        <div className="notice notice--error" role="alert" id="form-errors" tabIndex={-1}>
          <h2>Please fix {errorList.length === 1 ? "this field" : `these ${errorList.length} fields`}</h2>
          <ul>
            {errorList.map((k) => (
              <li key={k}>
                <a
                  href={`#field-${k}`}
                  onClick={(ev) => {
                    ev.preventDefault();
                    p.onFocusField(k);
                  }}
                >
                  {LABELS[k]}
                </a>
                : {e[k]}
              </li>
            ))}
          </ul>
        </div>
      )}

      <fieldset>
        <legend>The purchase</legend>
        <div className="grid2">
          {text("purchaseAmount", "purchaseAmount", { inputMode: "decimal", placeholder: "12000", hint: "Digits and an optional decimal part." })}
          {currency("purchaseCurrency")}
        </div>
        {text("desiredBy", "desiredBy", { type: "date", optional: true, hint: "Leave blank if there is no deadline." })}
        <label className="check">
          <input type="checkbox" checked={v.allowsPartial} onChange={(ev) => onChange({ allowsPartial: ev.target.checked })} />
          <span>Partial payment is allowed</span>
        </label>
      </fieldset>

      <fieldset>
        <legend>Your position</legend>
        {text("asOf", "asOf", { type: "date", hint: asOfHint })}
        <div className="grid2">
          {text("balance", "balance", { inputMode: "decimal", placeholder: "150000" })}
          {currency("homeCurrency")}
        </div>
        {text("balanceAsOf", "balanceAsOf", { type: "date", optional: true })}
        {text("reserve", "reserve", { inputMode: "decimal", placeholder: "30000", hint: "The balance you want to keep at all times." })}
      </fieldset>

      <fieldset id="field-methods" tabIndex={-1} aria-describedby={e.methods ? "field-methods-err" : undefined}>
        <legend>Payment approaches the engine may consider</legend>
        <div className="checks">
          {CANDIDATE_TYPES.map((t) => (
            <label className="check" key={t}>
              <input
                type="checkbox"
                checked={v.methods[t]}
                onChange={(ev) => onChange({ methods: { ...v.methods, [t]: ev.target.checked } })}
              />
              <span>{CANDIDATE_LABEL[t] ?? t}</span>
            </label>
          ))}
        </div>
        {e.methods && (
          <p id="field-methods-err" className="error-text">
            <span aria-hidden="true">⚠ </span>
            {e.methods}
          </p>
        )}
        {text("maxInstallmentDays", "maxInstallmentDays", { inputMode: "numeric", optional: true, hint: "Only used if installments are considered." })}
      </fieldset>

      {p.showMockControls && (
      <div className="mock-control mock-control--form">
        <label htmlFor="mock-scenario">Mock engine scenario</label>
        <select id="mock-scenario" value={p.scenario} onChange={(ev) => p.onScenario(ev.target.value as ScenarioKey)}>
          {SCENARIOS.map((s) => (
            <option key={s.key} value={s.key}>
              {s.label}
            </option>
          ))}
        </select>
        <p className="hint">The sample result comes from this choice. Your numbers are not used to compute it.</p>
      </div>
      )}

      <div className="actions">
        <button type="submit" className="btn btn--primary" disabled={p.busy} aria-disabled={p.busy}>
          {p.busy ? "Asking the engine…" : "Ask the engine"}
        </button>
        <button type="button" className="btn" onClick={p.onSample} disabled={p.busy}>
          Fill with sample inputs
        </button>
        <button type="button" className="btn btn--ghost" onClick={p.onClear} disabled={p.busy}>
          Clear
        </button>
      </div>
    </form>
  );
}
