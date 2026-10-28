/**
 * Wire types for the documented FinGuard API (docs/api/v1.md, backend/finguard_api/schemas.py, service.py).
 *
 * Money is ALWAYS a canonical decimal string (never a number). Responses are treated as untrusted data: fields
 * whose value set is open (status, severity, data quality) are typed `string` and validated where they are used.
 */

export type Money = string;
export type IsoDate = string;

export const STATUS_VALUES = ["affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"] as const;
export type StatusValue = (typeof STATUS_VALUES)[number];

export const CANDIDATE_TYPES = [
  "full_payment",
  "installments",
  "partial",
  "wait",
  "full_payment_with_spending_changes",
] as const;
export type CandidateTypeValue = (typeof CANDIDATE_TYPES)[number];

// ---- request (subset the prototype can build; unknown/extra fields are rejected by the real API) ----
export interface EventIn {
  event_id: string;
  event_date: IsoDate;
  amount: Money | null;
  currency: string;
  direction: string;
  status: string;
  category: string;
}

export interface ScheduleStepIn {
  due_date: IsoDate;
  amount: Money;
  currency: string;
}

export interface PaymentOptionIn {
  option_id: string;
  method: string;
  schedule: readonly ScheduleStepIn[];
  stated_total: Money;
  stated_total_currency: string;
}

export interface AnalysisRequest {
  as_of: IsoDate;
  profile: {
    home_currency: string;
    current_available_balance: Money;
    minimum_balance_to_keep: Money;
    balance_as_of?: IsoDate;
  };
  purchase: {
    amount: Money;
    currency: string;
    desired_completion_date?: IsoDate;
    allows_partial_payment: boolean;
  };
  preferences: {
    accepted_methods: readonly string[];
    max_installment_term_days?: number;
  };
  events?: readonly EventIn[];
  payment_options?: readonly PaymentOptionIn[];
  config?: { horizon_days?: number };
}
export type AnalysisRequestSample = AnalysisRequest;

// ---- response ----
export type ReasonParam = readonly [string, string];

export interface ReasonEntry {
  readonly code: string;
  readonly severity: string;
  readonly params: readonly ReasonParam[];
}

export interface ScheduleStep {
  readonly amount: Money;
  readonly currency: string;
  readonly due_date: IsoDate;
}

export interface SpendingChange {
  readonly target_id: string;
  readonly action: string;
  readonly category: string;
  readonly amount_changed: Money;
  readonly window_total_saving: Money;
  readonly occurrences: number;
}

export interface BreachDay {
  readonly day: IsoDate;
  readonly attribution: string;
  readonly baseline_low: Money;
  readonly plan_low: Money;
  readonly reserve: Money;
}

export interface Candidate {
  readonly candidate_type: string;
  readonly option_id: string | null;
  readonly safe: boolean;
  readonly eligible: boolean;
  readonly rejection_code: string | null;
  readonly first_payment_date: IsoDate | null;
  readonly final_payment_date: IsoDate | null;
  readonly total_cost: Money;
  readonly schedule: readonly ScheduleStep[];
  readonly spending_changes: readonly SpendingChange[];
  readonly breach_days: readonly BreachDay[];
  readonly reasons: readonly ReasonEntry[];
}

export interface MissingInfo {
  readonly code: string;
  readonly field_name: string;
  readonly impact: string;
  readonly subject_ids: readonly string[];
}

export interface CertifiableWindow {
  readonly start: IsoDate;
  readonly horizon_end: IsoDate;
  readonly deadline: IsoDate | null;
  readonly effective_end: IsoDate;
  readonly truncated: boolean;
  readonly max_window_days: number;
}

export interface BaselineSummary {
  readonly below_reserve: boolean;
  readonly first_breach_date: IsoDate | null;
  readonly last_breach_date: IsoDate | null;
  readonly days_below: number;
  readonly lowest: { readonly day: IsoDate; readonly balance: Money } | null;
  readonly max_shortfall: Money;
}

export interface AnalysisResultBody {
  readonly status: string | null;
  readonly certified: boolean;
  readonly chosen: Candidate | null;
  readonly candidates: readonly Candidate[];
  readonly reasons: readonly ReasonEntry[];
  readonly assumptions: readonly ReasonEntry[];
  readonly issues: readonly ReasonEntry[];
  readonly data_quality: string;
  readonly missing_information: readonly MissingInfo[];
  readonly certifiable_window: CertifiableWindow;
  readonly earliest_full_payment_date: IsoDate | null;
  readonly baseline_summary: BaselineSummary;
  readonly input_hash: string;
  readonly engine_version: string;
  // Present in the real response, not rendered by this prototype:
  readonly considered_commitments: readonly unknown[];
  readonly engine_config_echo: Readonly<Record<string, unknown>>;
  readonly fx_usage: readonly unknown[];
  readonly variable_spend: Readonly<Record<string, unknown>>;
}

export interface AnalyzeResponse {
  readonly api_version: string;
  readonly engine_version: string;
  readonly input_hash: string;
  readonly result_hash: string;
  readonly outcome: { readonly certified: boolean; readonly status: string | null };
  readonly result: AnalysisResultBody;
}

export interface LedgerDay {
  readonly day: IsoDate;
  readonly low: Money;
  readonly close: Money;
}

export interface ForecastResultBody {
  readonly baseline_series: readonly LedgerDay[];
  readonly baseline_summary: BaselineSummary;
  readonly certifiable_window: CertifiableWindow;
  readonly assumptions: readonly ReasonEntry[];
  readonly issues: readonly ReasonEntry[];
  readonly input_hash: string;
  readonly considered_commitments: readonly unknown[];
  readonly engine_config_echo: Readonly<Record<string, unknown>>;
  readonly fx_usage: readonly unknown[];
  readonly variable_spend: Readonly<Record<string, unknown>>;
}

export interface ForecastResponse {
  readonly api_version: string;
  readonly engine_version: string;
  readonly input_hash: string;
  readonly result_hash: string;
  readonly result: ForecastResultBody;
}

export interface ApiErrorBody {
  readonly error: { readonly code: string; readonly violations?: readonly string[] };
}

export interface ApiErrorResponse {
  readonly status: number;
  readonly body: ApiErrorBody;
}
