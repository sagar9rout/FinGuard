import { SAMPLE_AS_OF } from "./form.ts";

/**
 * The caller's calendar date, as YYYY-MM-DD, in the viewer's LOCAL time zone (local year/month/day, never
 * `toISOString()`, which is UTC and would show yesterday's date for part of the day in zones east of UTC).
 * The engine reads no clock; this is only the default for the editable "Analysis date" field in live mode.
 */
export function localIsoDate(now: Date): string {
  const p = (n: number, width: number) => String(n).padStart(width, "0");
  return `${p(now.getFullYear(), 4)}-${p(now.getMonth() + 1, 2)}-${p(now.getDate(), 2)}`;
}

/** Live mode starts from today's date; mock mode keeps the fixed sample date so its fixtures stay reproducible. */
export function defaultAsOf(kind: "mock" | "live", now: Date): string {
  return kind === "live" ? localIsoDate(now) : SAMPLE_AS_OF;
}

/** Both arguments are valid YYYY-MM-DD strings, which order correctly as text. */
export function isBeforeDay(day: string, other: string): boolean {
  return day < other;
}
