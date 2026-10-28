/**
 * The rule-based guided input collector behind the Assistant panel.
 *
 * This is NOT a language model and does not interpret free text. It looks at the structured form, asks for the next
 * missing or invalid required field, and reads the entered values back. It has no access to results and never states
 * or hints at an affordability outcome; only the engine decides.
 */
import { isValidIsoDate, validateForm, type FieldName, type FormValues } from "./form.ts";
import { formatDate, formatMoney, isCanonicalDecimal } from "./money.ts";
import { CANDIDATE_TYPES } from "../types/api.ts";

export const ASSISTANT_DISCLOSURE =
  "I am a guided form helper, not an AI model and not the decision-maker. I only help you fill in inputs. " +
  "The FinGuard engine alone determines the financial outcome, and in this prototype even the engine is a mock that returns sample results.";

export interface Question {
  readonly field: FieldName;
  readonly question: string;
  readonly hint: string;
  readonly input: "money" | "date" | "currency" | "methods";
}

const REQUIRED_ORDER: readonly Question[] = [
  { field: "asOf", question: "Which date should the analysis be as of?", hint: "YYYY-MM-DD. The engine never reads a clock, so you supply it.", input: "date" },
  { field: "homeCurrency", question: "What is your home currency?", hint: "Your balance and reserve are in this currency.", input: "currency" },
  { field: "balance", question: "What is your current available balance?", hint: "Digits and an optional decimal part, e.g. 84250.75.", input: "money" },
  { field: "reserve", question: "What minimum balance do you want to keep at all times?", hint: "The engine treats this as your reserve.", input: "money" },
  { field: "purchaseAmount", question: "How much is the purchase?", hint: "Greater than zero, e.g. 12000.", input: "money" },
  { field: "purchaseCurrency", question: "Which currency is the purchase priced in?", hint: "", input: "currency" },
  { field: "methods", question: "Which payment approaches may the engine consider?", hint: "Select at least one on the form.", input: "methods" },
];

/** The first required field that is empty or invalid, or null when every required field is valid. */
export function nextQuestion(values: FormValues): Question | null {
  const errors = validateForm(values);
  return REQUIRED_ORDER.find((q) => errors[q.field] !== undefined) ?? null;
}

export function missingFields(values: FormValues): readonly Question[] {
  const errors = validateForm(values);
  return REQUIRED_ORDER.filter((q) => errors[q.field] !== undefined);
}

export interface SummaryLine {
  readonly label: string;
  readonly value: string;
}

function money(value: string, currency: string): string {
  const v = value.trim();
  return isCanonicalDecimal(v) ? formatMoney(v, currency) : "not entered yet";
}
function date(value: string): string {
  const v = value.trim();
  return isValidIsoDate(v) ? formatDate(v) : "not entered yet";
}

/** Reads the entered values back; no judgement and no arithmetic. */
export function summarize(v: FormValues): readonly SummaryLine[] {
  const lines: SummaryLine[] = [
    { label: "Analysis date", value: date(v.asOf) },
    { label: "Current available balance", value: money(v.balance, v.homeCurrency) },
    { label: "Minimum balance to keep", value: money(v.reserve, v.homeCurrency) },
    { label: "Purchase amount", value: money(v.purchaseAmount, v.purchaseCurrency) },
    { label: "Partial payment allowed", value: v.allowsPartial ? "Yes" : "No" },
    { label: "Approaches the engine may consider", value: CANDIDATE_TYPES.filter((t) => v.methods[t]).join(", ") || "none selected" },
  ];
  if (v.desiredBy.trim() !== "") lines.push({ label: "Wanted by", value: date(v.desiredBy) });
  return lines;
}
