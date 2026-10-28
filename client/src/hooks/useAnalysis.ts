import { useCallback, useMemo, useRef, useState } from "react";
import type { AdapterError, AnalysisAdapter } from "../adapters/analysisAdapter.ts";
import { MockAdapter, SCENARIOS, type ScenarioKey } from "../adapters/mockAdapter.ts";
import { buildDecisionView, type DecisionView } from "../lib/decision.ts";
import { isResultStale, inputsKey } from "../lib/stale.ts";
import { defaultAsOf, localIsoDate } from "../lib/today.ts";
import { emptyForm, sampleForm, toRequest, validateForm, type FormValues } from "../lib/form.ts";

export type Outcome =
  | { readonly kind: "idle" }
  | { readonly kind: "loading" }
  | { readonly kind: "empty" }
  | { readonly kind: "error"; readonly error: AdapterError }
  | { readonly kind: "result"; readonly view: DecisionView; readonly scenarioLabel: string | null };

const CLIENT_ERROR: AdapterError = { status: 0, code: "client_error", violations: [] };

/**
 * Form state and the request/response cycle for the Buy or Wait page. Everything lives in memory: nothing the user
 * types is stored or logged; in live mode the request goes to the local API only. The result is whatever the adapter returns; nothing is computed here.
 */
export function useAnalysis(adapter: AnalysisAdapter) {
  const kind = adapter.kind;
  const [values, setValues] = useState<FormValues>(() => emptyForm(defaultAsOf(kind, new Date())));
  // The inputs behind the displayed result; when they change the result is out of date (never silently re-used).
  const [submittedKey, setSubmittedKey] = useState<string | null>(null);
  const [attempted, setAttempted] = useState(false);
  const [scenario, setScenario] = useState<ScenarioKey>("affordable_now");
  const [outcome, setOutcome] = useState<Outcome>({ kind: "idle" });
  const seq = useRef(0);

  const errors = useMemo(() => (attempted ? validateForm(values) : {}), [attempted, values]);
  const change = useCallback((patch: Partial<FormValues>) => setValues((v) => ({ ...v, ...patch })), []);

  const submit = useCallback(async (onStart?: () => void): Promise<boolean> => {
    setAttempted(true);
    if (Object.keys(validateForm(values)).length > 0) {
      setOutcome({ kind: "idle" });
      return false;
    }
    const id = ++seq.current;
    setSubmittedKey(inputsKey(values));
    setOutcome({ kind: "loading" });
    onStart?.();
    if (adapter instanceof MockAdapter) adapter.scenario = scenario;
    try {
      const r = await adapter.analyze(toRequest(values));
      if (id !== seq.current) return true;
      if (!r.ok) setOutcome({ kind: "error", error: r.error });
      else if ("empty" in r) setOutcome({ kind: "empty" });
      else {
        const label = adapter.kind === "mock" ? (SCENARIOS.find((s) => s.key === scenario)?.label ?? scenario) : null;
        setOutcome({ kind: "result", view: buildDecisionView(r.response, values.homeCurrency), scenarioLabel: label });
      }
    } catch {
      if (id === seq.current) setOutcome({ kind: "error", error: CLIENT_ERROR });
    }
    return true;
  }, [adapter, scenario, values]);

  const fillSample = useCallback(() => {
    setValues(sampleForm(defaultAsOf(kind, new Date())));
    setAttempted(false);
  }, [kind]);
  const clear = useCallback(() => {
    seq.current++;
    setValues(emptyForm(defaultAsOf(kind, new Date())));
    setSubmittedKey(null);
    setAttempted(false);
    setOutcome({ kind: "idle" });
  }, [kind]);

  const stale = isResultStale(outcome.kind === "result", submittedKey, values);
  const today = kind === "live" ? localIsoDate(new Date()) : null;

  return { values, errors, stale, today, scenario, setScenario, outcome, busy: outcome.kind === "loading", change, submit, fillSample, clear };
}
