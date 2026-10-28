import type { FormValues } from "./form.ts";

/** A comparable snapshot of the form inputs. Used only to tell whether a displayed result still matches the form. */
export function inputsKey(values: FormValues): string {
  return JSON.stringify(values);
}

/** True when a result is on screen and the form has changed since it was requested. Never true before any submit. */
export function isResultStale(hasResult: boolean, submittedKey: string | null, values: FormValues): boolean {
  return hasResult && submittedKey !== null && submittedKey !== inputsKey(values);
}
