/**
 * The Decision Card view-model. Everything the card shows is a re-labelled copy of the engine response.
 *
 * Order of interpretation is fixed (docs/api/v1.md, ADR 0011 point 5): `outcome.certified` is read FIRST.
 *  - certified === false  -> "could not be certified". `status` is ignored, even if a malformed response carries
 *                            one, and it is never rendered as "not affordable".
 *  - certified === true   -> `status` must be one of the four documented values; anything else is "unreadable".
 *  - envelope and result disagreeing about `certified` -> "unreadable" (we do not guess).
 * Nothing here computes, ranks or re-derives a verdict.
 */
import { formatDate, formatMoney } from "./money.ts";
import { describeReasons, type ReasonView } from "./reasons.ts";
import { STATUS_VALUES, type AnalyzeResponse, type Candidate, type StatusValue } from "../types/api.ts";

export const STATUS_LABEL: Readonly<Record<StatusValue, string>> = {
  affordable_now: "Affordable now",
  affordable_with_plan: "Affordable with a plan",
  affordable_later: "Affordable later",
  not_affordable: "Not affordable",
};

export type Tone = "now" | "plan" | "later" | "not" | "uncertified" | "unreadable";
const TONE: Readonly<Record<StatusValue, Tone>> = {
  affordable_now: "now",
  affordable_with_plan: "plan",
  affordable_later: "later",
  not_affordable: "not",
};

export const CANDIDATE_LABEL: Readonly<Record<string, string>> = {
  full_payment: "Full payment",
  installments: "Installments",
  partial: "Partial payment",
  wait: "Wait, then pay in full",
  full_payment_with_spending_changes: "Full payment with spending changes",
};

const QUALITY_LABEL: Readonly<Record<string, string>> = {
  high: "High",
  medium: "Medium",
  low: "Low",
  insufficient: "Insufficient",
};

export const UNCERTIFIED_EXPLANATION =
  "The engine could not certify this analysis, so it has produced no affordability verdict. " +
  "This is not the same as “not affordable”.";
export const UNREADABLE_EXPLANATION =
  "The response could not be interpreted safely, so no verdict is shown. Nothing has been assumed.";

export interface ScheduleRow {
  readonly date: string;
  readonly amount: string;
}
export interface SpendingChangeRow {
  readonly action: string;
  readonly category: string;
  readonly amount: string;
}
export interface CandidateView {
  readonly typeLabel: string;
  readonly optionId: string | null;
  readonly firstPayment: string | null;
  readonly finalPayment: string | null;
  readonly totalCost: string;
  readonly schedule: readonly ScheduleRow[];
  readonly spendingChanges: readonly SpendingChangeRow[];
  readonly reasons: readonly ReasonView[];
}
export interface MissingView {
  readonly field: string;
  readonly impact: string;
  readonly reason: ReasonView;
}
export interface DecisionDetails {
  readonly reasons: readonly ReasonView[];
  readonly assumptions: readonly ReasonView[];
  readonly issues: readonly ReasonView[];
  readonly missing: readonly MissingView[];
  readonly dataQuality: string;
  readonly candidate: CandidateView | null;
  readonly earliestFullPayment: string | null;
  readonly window: string;
  readonly engineVersion: string;
  readonly inputHash: string;
  readonly resultHash: string;
}

export type DecisionView =
  | { readonly kind: "verdict"; readonly status: StatusValue; readonly headline: string; readonly tone: Tone; readonly details: DecisionDetails }
  | { readonly kind: "uncertified"; readonly headline: string; readonly tone: "uncertified"; readonly explanation: string; readonly details: DecisionDetails }
  | { readonly kind: "unreadable"; readonly headline: string; readonly tone: "unreadable"; readonly explanation: string };

function isStatus(value: unknown): value is StatusValue {
  return typeof value === "string" && (STATUS_VALUES as readonly string[]).includes(value);
}

function candidateView(c: Candidate, currency: string): CandidateView {
  return {
    typeLabel: CANDIDATE_LABEL[c.candidate_type] ?? c.candidate_type,
    optionId: c.option_id,
    firstPayment: c.first_payment_date === null ? null : formatDate(c.first_payment_date),
    finalPayment: c.final_payment_date === null ? null : formatDate(c.final_payment_date),
    totalCost: formatMoney(c.total_cost, currency),
    schedule: c.schedule.map((s) => ({ date: formatDate(s.due_date), amount: formatMoney(s.amount, s.currency) })),
    spendingChanges: c.spending_changes.map((s) => ({
      action: s.action,
      category: s.category,
      amount: formatMoney(s.amount_changed, currency),
    })),
    reasons: describeReasons(c.reasons, currency),
  };
}

function details(r: AnalyzeResponse, currency: string): DecisionDetails {
  const res = r.result;
  const w = res.certifiable_window;
  return {
    reasons: describeReasons(res.reasons, currency),
    assumptions: describeReasons(res.assumptions, currency),
    issues: describeReasons(res.issues, currency),
    missing: res.missing_information.map((m) => ({
      field: m.field_name,
      impact: m.impact === "could_change_decision" ? "Could change the decision" : m.impact === "informational" ? "Informational" : m.impact,
      reason: describeReasons([{ code: m.code, severity: "info", params: [] }], currency)[0] as ReasonView,
    })),
    dataQuality: QUALITY_LABEL[res.data_quality] ?? res.data_quality,
    candidate: res.chosen === null ? null : candidateView(res.chosen, currency),
    earliestFullPayment: res.earliest_full_payment_date === null ? null : formatDate(res.earliest_full_payment_date),
    window: `${formatDate(w.start)} to ${formatDate(w.effective_end)}${w.truncated ? " (truncated)" : ""}`,
    engineVersion: r.engine_version,
    inputHash: r.input_hash,
    resultHash: r.result_hash,
  };
}

export function buildDecisionView(response: AnalyzeResponse, homeCurrency: string): DecisionView {
  const unreadable = (): DecisionView => ({
    kind: "unreadable",
    headline: "Result could not be read",
    tone: "unreadable",
    explanation: UNREADABLE_EXPLANATION,
  });
  const envelopeCertified: unknown = response?.outcome?.certified;
  const resultCertified: unknown = response?.result?.certified;
  if (typeof envelopeCertified !== "boolean" || envelopeCertified !== resultCertified) return unreadable();

  if (!envelopeCertified) {
    return {
      kind: "uncertified",
      headline: "Could not be certified",
      tone: "uncertified",
      explanation: UNCERTIFIED_EXPLANATION,
      details: details(response, homeCurrency),
    };
  }
  const status: unknown = response.outcome.status;
  if (!isStatus(status) || response.result.status !== status) return unreadable();
  return { kind: "verdict", status, headline: STATUS_LABEL[status], tone: TONE[status], details: details(response, homeCurrency) };
}
