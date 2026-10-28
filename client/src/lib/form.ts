/**
 * The "Buy or Wait?" form model: structural validation only (the same shape rules the documented API enforces:
 * money is a decimal string, never a float; dates are YYYY-MM-DD). It never judges affordability.
 *
 * Optional API inputs the prototype does not collect (events, commitments, payment options, FX rates, evidence)
 * are simply left out of the request, so the engine would use its documented defaults.
 */
import { CANDIDATE_TYPES, type AnalysisRequest, type CandidateTypeValue } from "../types/api.ts";

export interface FormValues {
  asOf: string;
  homeCurrency: string;
  balance: string;
  balanceAsOf: string;
  reserve: string;
  purchaseAmount: string;
  purchaseCurrency: string;
  desiredBy: string;
  allowsPartial: boolean;
  methods: Readonly<Record<CandidateTypeValue, boolean>>;
  maxInstallmentDays: string;
}

export type FieldName = Exclude<keyof FormValues, "allowsPartial">;
export type FieldErrors = Partial<Record<FieldName, string>>;

/**
 * The fixed analysis date of the mock mode and of the committed synthetic fixtures (deliberately constant, so they
 * are reproducible). Live mode does NOT use it: it defaults to today's local date (lib/today.ts).
 */
export const SAMPLE_AS_OF = "2026-10-24";

export function emptyForm(asOf: string = SAMPLE_AS_OF): FormValues {
  return {
    asOf,
    homeCurrency: "INR",
    balance: "",
    balanceAsOf: "",
    reserve: "",
    purchaseAmount: "",
    purchaseCurrency: "INR",
    desiredBy: "",
    allowsPartial: true,
    methods: Object.fromEntries(CANDIDATE_TYPES.map((t) => [t, true])) as Record<CandidateTypeValue, boolean>,
    maxInstallmentDays: "",
  };
}

const DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] as const;

export function isValidIsoDate(value: string): boolean {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (m === null) return false;
  const year = Number(m[1]);
  const month = Number(m[2]);
  const day = Number(m[3]);
  if (month < 1 || month > 12 || year < 1) return false;
  const leap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  const max = month === 2 && leap ? 29 : (DAYS_IN_MONTH[month - 1] as number);
  return day >= 1 && day <= max;
}

// Mirrors backend/finguard_api validation limits: |amount| < 10^15 and at most 10 fractional digits.
const MONEY = /^(\d{1,15})(\.\d{1,10})?$/;
const ZERO = /^0*(\.0*)?$/;

export function isMoneyText(value: string): boolean {
  return MONEY.test(value.trim());
}

export function validateForm(v: FormValues): FieldErrors {
  const e: FieldErrors = {};
  const currencyOk = (c: string): boolean => /^[A-Z]{3}$/.test(c);

  if (v.asOf.trim() === "") e.asOf = "Enter the analysis date (YYYY-MM-DD).";
  else if (!isValidIsoDate(v.asOf.trim())) e.asOf = "Use a real calendar date in YYYY-MM-DD form.";

  if (!currencyOk(v.homeCurrency)) e.homeCurrency = "Choose your home currency.";

  if (v.balance.trim() === "") e.balance = "Enter your current available balance.";
  else if (!isMoneyText(v.balance)) e.balance = "Use digits with an optional decimal part, for example 84250.75. No commas, signs or symbols.";

  if (v.reserve.trim() === "") e.reserve = "Enter the minimum balance you want to keep.";
  else if (!isMoneyText(v.reserve)) e.reserve = "Use digits with an optional decimal part, for example 30000. No commas, signs or symbols.";

  if (v.purchaseAmount.trim() === "") e.purchaseAmount = "Enter the purchase amount.";
  else if (!isMoneyText(v.purchaseAmount)) e.purchaseAmount = "Use digits with an optional decimal part, for example 12000. No commas, signs or symbols.";
  else if (ZERO.test(v.purchaseAmount.trim())) e.purchaseAmount = "The purchase amount must be greater than zero.";

  if (!currencyOk(v.purchaseCurrency)) e.purchaseCurrency = "Choose the purchase currency.";

  if (v.balanceAsOf.trim() !== "" && !isValidIsoDate(v.balanceAsOf.trim())) e.balanceAsOf = "Use a real calendar date in YYYY-MM-DD form, or leave blank.";

  if (v.desiredBy.trim() !== "") {
    if (!isValidIsoDate(v.desiredBy.trim())) e.desiredBy = "Use a real calendar date in YYYY-MM-DD form, or leave blank.";
    else if (!e.asOf && v.desiredBy.trim() < v.asOf.trim()) e.desiredBy = "The desired date cannot be before the analysis date.";
  }

  if (!CANDIDATE_TYPES.some((t) => v.methods[t])) e.methods = "Select at least one payment approach the engine may consider.";

  if (v.maxInstallmentDays.trim() !== "" && !/^[1-9]\d{0,3}$/.test(v.maxInstallmentDays.trim()))
    e.maxInstallmentDays = "Use a whole number of days (1 to 9999), or leave blank.";
  return e;
}

/** Build the documented request body from a VALID form. Money stays a string. */
export function toRequest(v: FormValues): AnalysisRequest {
  const trim = (s: string): string => s.trim();
  const profile: AnalysisRequest["profile"] = {
    home_currency: v.homeCurrency,
    current_available_balance: trim(v.balance),
    minimum_balance_to_keep: trim(v.reserve),
    ...(trim(v.balanceAsOf) === "" ? {} : { balance_as_of: trim(v.balanceAsOf) }),
  };
  const purchase: AnalysisRequest["purchase"] = {
    amount: trim(v.purchaseAmount),
    currency: v.purchaseCurrency,
    allows_partial_payment: v.allowsPartial,
    ...(trim(v.desiredBy) === "" ? {} : { desired_completion_date: trim(v.desiredBy) }),
  };
  const preferences: AnalysisRequest["preferences"] = {
    accepted_methods: CANDIDATE_TYPES.filter((t) => v.methods[t]),
    ...(trim(v.maxInstallmentDays) === "" ? {} : { max_installment_term_days: Number(trim(v.maxInstallmentDays)) }),
  };
  return { as_of: trim(v.asOf), profile, purchase, preferences };
}

/**
 * Sample inputs for the "Fill with sample inputs" button (invented values). With the fixed sample date the deadline is
 * the committed 2026-11-30; with any other analysis date no deadline is set, so no date is derived or guessed here.
 */
export function sampleForm(asOf: string = SAMPLE_AS_OF): FormValues {
  return {
    ...emptyForm(asOf),
    balance: "150000",
    balanceAsOf: asOf,
    reserve: "30000",
    purchaseAmount: "12000",
    desiredBy: asOf === SAMPLE_AS_OF ? "2026-11-30" : "",
  };
}
