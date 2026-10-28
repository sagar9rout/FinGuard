import type { AdapterError } from "../../adapters/analysisAdapter.ts";
import { classifyError } from "../../lib/errorKind.ts";

/** Nothing has been submitted yet. */
export function IdleState() {
  return (
    <section className="empty" aria-labelledby="idle-h">
      <h2 id="idle-h">No analysis yet</h2>
      <p>Complete the form and ask the engine. The result appears here, with its reasons, assumptions and any missing information.</p>
    </section>
  );
}

export function LoadingState() {
  return (
    <div className="skeleton" role="status" aria-live="polite" aria-busy="true">
      <span className="sr-only">Waiting for the engine…</span>
      <div className="skeleton__row" />
      <div className="skeleton__row skeleton__row--tall" />
    </div>
  );
}

/** The adapter answered with no result at all. */
export function EmptyResultState() {
  return (
    <section className="empty" aria-labelledby="empty-h" role="status">
      <h2 id="empty-h">The engine returned no result</h2>
      <p>There is nothing to show. No verdict has been assumed. Try again.</p>
    </section>
  );
}

const COPY = {
  validation: [
    "The engine rejected this request",
    "The request did not pass the engine's validation, so no analysis was run. Nothing has been assumed.",
  ],
  unavailable: [
    "The engine could not be reached",
    "The local API did not answer (it may not be running, or this page's origin may not be allowed by it). No verdict is shown and nothing has been assumed.",
  ],
  unexpected: [
    "Something went wrong",
    "The engine could not complete the request. No verdict is shown and nothing has been assumed.",
  ],
} as const;

export function ErrorState({ error }: { error: AdapterError }) {
  const [title, text] = COPY[classifyError(error)];
  return (
    <section className="notice notice--error" role="alert" aria-labelledby="err-h">
      <h2 id="err-h">{title}</h2>
      <p>{text}</p>
      <p className="muted small">
        Code <code>{error.code}</code> · status {error.status}
      </p>
      {error.violations.length > 0 && (
        <ul className="plain">
          {error.violations.map((v) => (
            <li key={v}>
              <code>{v}</code>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
