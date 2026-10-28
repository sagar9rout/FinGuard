/**
 * Reason-code copy, extracted verbatim (backticks removed) from docs/engine/reason-codes.md, which is marked DRAFT there.
 * Generated once at authoring time; do not hand-edit. Codes the engine can emit but the document does not list
 * (OBLIGATION_BEFORE_INCOME, INCOME_ARRIVES_LATER) are deliberately absent so the UI shows its neutral fallback.
 */
export type ReasonCategory = "reason" | "assumption" | "issue";

export const REASON_COPY: Readonly<Record<string, { readonly category: ReasonCategory; readonly copy: string }>> = {
  "PAY_NOW_SAFE": {
    "category": "reason",
    "copy": "Full payment today is safe with no changes"
  },
  "PLAN_SAFE_INSTALLMENTS": {
    "category": "reason",
    "copy": "A supplied installment option is safe"
  },
  "PLAN_SAFE_PARTIAL": {
    "category": "reason",
    "copy": "A constructed partial-payment plan is safe"
  },
  "PLAN_SAFE_WAIT": {
    "category": "reason",
    "copy": "A later full payment is safe"
  },
  "PLAN_SAFE_WITH_SPENDING_CHANGES": {
    "category": "reason",
    "copy": "Full payment today is safe once listed changes are applied"
  },
  "NO_SAFE_OPTION": {
    "category": "reason",
    "copy": "No eligible candidate was safe within the certifiable window"
  },
  "RESERVE_BREACH_IF_PAID_NOW": {
    "category": "reason",
    "copy": "Paying now would breach the reserve; carries date, shortfall, and a cause of purchase_causes, worsens_existing, or unrelated"
  },
  "LOWEST_POINT": {
    "category": "reason",
    "copy": "The lowest point of the relevant forecast series, with date and balance"
  },
  "BASELINE_BELOW_RESERVE": {
    "category": "reason",
    "copy": "The user's own baseline (no purchase) is below reserve on one or more days; never used to reject a candidate by itself"
  },
  "PURCHASE_CAUSES_BREACH": {
    "category": "reason",
    "copy": "Baseline was safe that day, the plan is not (causes)"
  },
  "PURCHASE_WORSENS_EXISTING_BREACH": {
    "category": "reason",
    "copy": "Baseline was already unsafe that day, and the plan lowers it further (worsens)"
  },
  "PURCHASE_UNRELATED_TO_BREACH": {
    "category": "reason",
    "copy": "Baseline was already unsafe that day, and the plan does not worsen it; the shortfall on that day cannot be attributed to the candidate (unrelated). Always emitted explicitly for every such day — never merged into PURCHASE_WORSENS_EXISTING_BREACH or silently dropped."
  },
  "REJECTED_UNSAFE": {
    "category": "reason",
    "copy": "A candidate failed the safety predicate (superseded in explanatory detail by PURCHASE_CAUSES_BREACH / PURCHASE_WORSENS_EXISTING_BREACH / PURCHASE_UNRELATED_TO_BREACH, retained as a summary code)"
  },
  "REJECTED_DEADLINE": {
    "category": "reason",
    "copy": "A candidate's final payment is after the requested deadline"
  },
  "REJECTED_BEYOND_CERTIFIABLE_WINDOW": {
    "category": "reason",
    "copy": "A candidate's final payment is after effective_end"
  },
  "REJECTED_INVALID_OPTION": {
    "category": "reason",
    "copy": "A supplied payment option failed structural validation"
  },
  "METHOD_NOT_ACCEPTED": {
    "category": "reason",
    "copy": "The method isn't in the user's accepted list"
  },
  "INSTALLMENTS_NOT_CONSIDERED": {
    "category": "reason",
    "copy": "The user has not set a maximum installment term"
  },
  "INSTALLMENT_TERM_EXCEEDS_LIMIT": {
    "category": "reason",
    "copy": "Installment term exceeds the user's stated maximum"
  },
  "PARTIAL_NOT_ALLOWED_BY_REQUEST": {
    "category": "reason",
    "copy": "The purchase request does not allow partial payment"
  },
  "SAFE_OPTION_EXCLUDED_BY_PREFERENCE": {
    "category": "reason",
    "copy": "A safe option exists but the method isn't accepted"
  },
  "SPENDING_CHANGE_PROPOSED": {
    "category": "reason",
    "copy": "One or more spending changes were found to rescue a candidate"
  },
  "SPENDING_CHANGE_INSUFFICIENT": {
    "category": "reason",
    "copy": "No combination of eligible changes rescues the candidate"
  },
  "NO_ELIGIBLE_FLEXIBLE_ITEMS": {
    "category": "reason",
    "copy": "No events are eligible for spending changes"
  },
  "CATEGORY_PROTECTED": {
    "category": "reason",
    "copy": "A category was excluded from spending changes because it's protected"
  },
  "CERTIFICATION_LIMITED_TO_WINDOW": {
    "category": "reason",
    "copy": "The deadline exceeds the certifiable window; certification covers only the window"
  },
  "UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION": {
    "category": "reason",
    "copy": "A debit's currency could not be resolved even within the bounded FX window"
  },
  "PENDING_DEBIT_RESERVED": {
    "category": "assumption",
    "copy": "A pending debit was reserved against spendable cash"
  },
  "OVERDUE_PENDING_DEBIT_RESERVED": {
    "category": "assumption",
    "copy": "An overdue pending debit was reserved at as_of"
  },
  "PENDING_CREDIT_EXCLUDED": {
    "category": "assumption",
    "copy": "A pending credit was not counted"
  },
  "UNREALIZED_EXCLUDED": {
    "category": "assumption",
    "copy": "An unrealized/non-cash event was excluded"
  },
  "SCHEDULED_INCOME_COUNTED": {
    "category": "assumption",
    "copy": "An explicitly scheduled credit was counted"
  },
  "SAME_DAY_CREDIT_AFTER_DEBITS": {
    "category": "assumption",
    "copy": "A same-day credit was counted after that day's debits"
  },
  "INTERNAL_TRANSFER_NEUTRAL": {
    "category": "assumption",
    "copy": "A matched internal-transfer pair was excluded from spend/change estimation"
  },
  "RECURRING_EXPENSE_PROJECTED": {
    "category": "assumption",
    "copy": "A detected recurring expense was projected forward"
  },
  "RECURRING_INCOME_CONFIRMED_INCLUDED": {
    "category": "assumption",
    "copy": "A confirmed recurring income commitment was counted"
  },
  "RECURRING_INCOME_UNCONFIRMED_EXCLUDED": {
    "category": "assumption",
    "copy": "A detected but unconfirmed recurring income was shown but not counted"
  },
  "COMMITMENT_LAPSED": {
    "category": "assumption",
    "copy": "A detected commitment's last occurrence is too old to project"
  },
  "COMMITMENT_OVERLAP_SUPPRESSED": {
    "category": "assumption",
    "copy": "A lower-precedence commitment was suppressed by a higher-precedence, overlapping one"
  },
  "COMMITMENT_REJECTED_BY_USER": {
    "category": "assumption",
    "copy": "A commitment was suppressed because the user rejected or disabled it"
  },
  "EXPLICIT_EVENT_SUPPRESSED_PROJECTION": {
    "category": "assumption",
    "copy": "A projected commitment occurrence was suppressed by a matching explicit event"
  },
  "VARIABLE_SPEND_ESTIMATED": {
    "category": "assumption",
    "copy": "Essential variable spend was estimated; carries method, lookback window, weeks used, categories, and resulting daily amount"
  },
  "VARIABLE_SPEND_INSUFFICIENT_HISTORY": {
    "category": "assumption",
    "copy": "Not enough history to produce a variable-spend estimate"
  },
  "VARIABLE_SPEND_PLUS_EXPLICIT_EVENTS": {
    "category": "assumption",
    "copy": "Explicit events in an estimated category were counted in addition to the estimate"
  },
  "DEADLINE_DEFAULTED": {
    "category": "assumption",
    "copy": "No desired-by date was supplied; the horizon end was used"
  },
  "SELLER_PRICE_ASSUMED_UNCHANGED": {
    "category": "assumption",
    "copy": "A constructed candidate (wait, partial, changes) assumed the full-payment price is stable over time"
  },
  "PLAN_EXTENDS_BEYOND_HORIZON": {
    "category": "assumption",
    "copy": "A plan runs past horizon_end but within effective_end"
  },
  "FX_PRIOR_RATE_USED": {
    "category": "assumption",
    "copy": "A rate from before the exact date was used, within the prior window"
  },
  "FX_INVERSE_USED": {
    "category": "assumption",
    "copy": "A rate's inverse was used because the stated direction wasn't available"
  },
  "FX_TRIANGULATED": {
    "category": "assumption",
    "copy": "A conversion was resolved via a pivot currency"
  },
  "FX_PESSIMISTIC_BOUND_USED": {
    "category": "assumption",
    "copy": "The bounded pessimistic FX fallback was used; carries the window, candidates considered, and chosen rate"
  },
  "UNCONVERTIBLE_CREDIT_EXCLUDED": {
    "category": "assumption",
    "copy": "A credit's currency could not be resolved and was excluded (non-blocking)"
  },
  "FACT_APPLIED": {
    "category": "assumption",
    "copy": "A confirmed fact was applied"
  },
  "FACT_APPLIED_UNCONFIRMED_CONSERVATIVE": {
    "category": "assumption",
    "copy": "A reducing fact was applied while still unconfirmed"
  },
  "FACT_UNCONFIRMED_IGNORED": {
    "category": "assumption",
    "copy": "An increasing fact was not applied because it isn't confirmed"
  },
  "FACT_CONFLICT": {
    "category": "assumption",
    "copy": "Two facts conflicted on the same target; resolved per the documented precedence"
  },
  "HYPOTHETICAL_INCOME_INCLUDED": {
    "category": "assumption",
    "copy": "A scenario override included hypothetical, non-confirmed income"
  },
  "COMMITMENT_DISABLED_BY_SCENARIO": {
    "category": "assumption",
    "copy": "A scenario override disabled a commitment for that run only"
  },
  "BALANCE_STALE": {
    "category": "issue",
    "copy": "The opening balance snapshot is older than a configured threshold"
  },
  "UNRESOLVED_AMOUNT": {
    "category": "issue",
    "copy": "An event has no usable amount and was excluded"
  },
  "MISSING_EVENT_DATE": {
    "category": "issue",
    "copy": "An event is missing a usable date"
  },
  "SETTLED_EVENT_IN_FUTURE": {
    "category": "issue",
    "copy": "A settled event is dated after as_of"
  },
  "OVERDUE_SCHEDULED": {
    "category": "issue",
    "copy": "A scheduled debit's date has already passed"
  },
  "INSUFFICIENT_HISTORY": {
    "category": "issue",
    "copy": "Too little history to support recurrence or variable-spend estimation"
  },
  "OPTION_TOTAL_MISMATCH": {
    "category": "issue",
    "copy": "A supplied payment option's stated total doesn't match its schedule within tolerance"
  },
  "DEADLINE_BEYOND_CERTIFIABLE_WINDOW": {
    "category": "issue",
    "copy": "The requested deadline exceeds what the engine can certify"
  },
  "UNCONVERTIBLE_DEBIT": {
    "category": "issue",
    "copy": "See UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION above"
  }
};
