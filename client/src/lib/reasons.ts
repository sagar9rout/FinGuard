/**
 * Turning engine reason entries into display data. The engine emits codes and structured parameters, never prose.
 * Copy comes ONLY from docs/engine/reason-codes.md (see reasonCopyData.ts). Parameters are shown as labelled
 * structured values; no sentence is invented from them. An unmapped code gets a neutral fallback.
 */
import { formatDate, formatMoney, isCanonicalDecimal } from "./money.ts";
import { REASON_COPY, type ReasonCategory } from "./reasonCopyData.ts";
import type { ReasonEntry } from "../types/api.ts";

export const FALLBACK_COPY = "No approved description is available for this engine code. The code is shown as the engine sent it.";

export type SeverityView = "info" | "warn" | "blocking" | "unknown";

export interface ParamView {
  readonly key: string;
  readonly label: string;
  readonly value: string;
  readonly kind: "money" | "date" | "text";
}

export interface ReasonView {
  readonly code: string;
  readonly severity: SeverityView;
  readonly category: ReasonCategory | "unmapped";
  readonly text: string;
  readonly mapped: boolean;
  readonly params: readonly ParamView[];
}

// Parameter keys documented in docs/engine/reason-codes.md and emitted in home-currency money / ISO dates.
const MONEY_KEYS: ReadonlySet<string> = new Set(["balance", "max_shortfall", "shortfall"]);
const DATE_KEYS: ReadonlySet<string> = new Set(["date", "first", "last"]);

export function severityView(raw: string): SeverityView {
  return raw === "info" || raw === "warn" || raw === "blocking" ? raw : "unknown";
}

export function describeParam(key: string, value: string, currency: string): ParamView {
  const label = key.replaceAll("_", " ");
  if (MONEY_KEYS.has(key) && isCanonicalDecimal(value)) return { key, label, value: formatMoney(value, currency), kind: "money" };
  if (DATE_KEYS.has(key) && /^\d{4}-\d{2}-\d{2}$/.test(value)) return { key, label, value: formatDate(value), kind: "date" };
  return { key, label, value, kind: "text" };
}

export function describeReason(entry: ReasonEntry, currency: string): ReasonView {
  const known = Object.hasOwn(REASON_COPY, entry.code) ? REASON_COPY[entry.code] : undefined;
  return {
    code: entry.code,
    severity: severityView(entry.severity),
    category: known?.category ?? "unmapped",
    text: known?.copy ?? FALLBACK_COPY,
    mapped: known !== undefined,
    params: entry.params.map(([k, v]) => describeParam(k, v, currency)),
  };
}

export function describeReasons(entries: readonly ReasonEntry[], currency: string): readonly ReasonView[] {
  return entries.map((e) => describeReason(e, currency));
}
