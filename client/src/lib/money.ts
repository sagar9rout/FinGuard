/**
 * Money display. Amounts are canonical decimal STRINGS from the engine; this module only re-formats text.
 *
 * - No Number/parseFloat/arithmetic: digits are never converted to floating point.
 * - No rounding: if the engine sends more fractional digits than the currency exponent and the extra digits are
 *   not all zero, they are shown as-is (the engine already rounds at its documented boundaries, ADR 0006).
 * - Exponents come from the currency registry. The request carries no `currencies` override, so the engine's
 *   default registry applies (backend/finguard_core/currency.py: INR, USD, EUR, ZAR, IDR, all exponent 2).
 *   A currency outside this table is shown with the engine's own digits and its code, without padding.
 */

export const CURRENCY_EXPONENTS: Readonly<Record<string, number>> = {
  INR: 2,
  USD: 2,
  EUR: 2,
  ZAR: 2,
  IDR: 2,
};

export const SUPPORTED_CURRENCIES = Object.keys(CURRENCY_EXPONENTS);

const CANONICAL_DECIMAL = /^-?\d+(\.\d+)?$/;
export const PLACEHOLDER = "—";
const NBSP = " ";
const MINUS = "−";

export function isCanonicalDecimal(value: string): boolean {
  return CANONICAL_DECIMAL.test(value);
}

export function currencyExponent(code: string): number | null {
  return Object.hasOwn(CURRENCY_EXPONENTS, code) ? (CURRENCY_EXPONENTS[code] ?? null) : null;
}

function group(integerDigits: string, indian: boolean): string {
  if (integerDigits.length <= 3) return integerDigits;
  const tail = integerDigits.slice(-3);
  let rest = integerDigits.slice(0, -3);
  const size = indian ? 2 : 3;
  const parts: string[] = [];
  while (rest.length > size) {
    parts.unshift(rest.slice(-size));
    rest = rest.slice(0, -size);
  }
  if (rest.length > 0) parts.unshift(rest);
  return `${parts.join(",")},${tail}`;
}

/** Format a canonical decimal string for display, e.g. ("84250.75","INR") -> "INR 84,250.75". Invalid input -> "—". */
export function formatMoney(value: string, currency: string): string {
  if (!isCanonicalDecimal(value)) return PLACEHOLDER;
  const negative = value.startsWith("-");
  const unsigned = negative ? value.slice(1) : value;
  const dot = unsigned.indexOf(".");
  const rawInt = dot === -1 ? unsigned : unsigned.slice(0, dot);
  let frac = dot === -1 ? "" : unsigned.slice(dot + 1);
  const intDigits = rawInt.replace(/^0+(?=\d)/, "");

  const exponent = currencyExponent(currency);
  if (exponent !== null) {
    if (frac.length < exponent) frac = frac.padEnd(exponent, "0");
    else if (frac.length > exponent && /^0*$/.test(frac.slice(exponent))) frac = frac.slice(0, exponent);
  }
  const allZero = /^0*$/.test(intDigits) && /^0*$/.test(frac);
  const body = group(intDigits, currency === "INR") + (frac.length > 0 ? `.${frac}` : "");
  return `${negative && !allZero ? MINUS : ""}${currency}${NBSP}${body}`;
}

const MONTHS: Readonly<Record<string, string>> = {
  "01": "Jan",
  "02": "Feb",
  "03": "Mar",
  "04": "Apr",
  "05": "May",
  "06": "Jun",
  "07": "Jul",
  "08": "Aug",
  "09": "Sep",
  "10": "Oct",
  "11": "Nov",
  "12": "Dec",
};

/** "2026-10-24" -> "24 Oct 2026". Pure string handling (no Date, no time zone). Unparseable input is returned as-is. */
export function formatDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (m === null) return iso;
  const month = Object.hasOwn(MONTHS, m[2] ?? "") ? MONTHS[m[2] ?? ""] : undefined;
  if (month === undefined || m[3] === undefined || m[3] === "00") return iso;
  return `${m[3].replace(/^0/, "")} ${month} ${m[1]}`;
}
