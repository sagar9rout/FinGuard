import { useEffect, useRef } from "react";
import type { DecisionDetails, DecisionView } from "../../lib/decision.ts";
import { ReasonList } from "./ReasonList.tsx";

interface Props {
  readonly view: DecisionView;
  /** What the mock engine was set to; shown so a sample result is never mistaken for a calculation on the inputs. */
  readonly scenarioLabel: string | null;
  /** The form inputs changed after this result was returned. */
  readonly stale?: boolean;
}

/**
 * Displays an engine result. `view` is built by buildDecisionView, which reads `outcome.certified` first; this
 * component only lays that view out and decides nothing. Uncertified results never read as "not affordable".
 */
export function DecisionCard({ view, scenarioLabel, stale = false }: Props) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, [view]);

  const kicker =
    view.kind === "verdict" ? "Engine result · certified" : view.kind === "uncertified" ? "Engine result · not certified" : "Result unreadable";

  return (
    <article className="decision" data-tone={view.tone} data-kind={view.kind} data-stale={stale ? "true" : undefined} aria-labelledby="decision-h">
      {stale && (
        <p className="notice notice--warn" role="status">
          Out of date: the inputs have changed since the engine returned this result. Press “Ask the engine” again; this result is not
          for the inputs now in the form.
        </p>
      )}
      <header className="decision__head">
        <p className="kicker">{kicker}</p>
        <h2 id="decision-h" ref={heading} tabIndex={-1}>
          {view.headline}
        </h2>
        {view.kind === "verdict" && (
          <p className="decision__sub">This is the engine&apos;s output, shown as received. FinGuard&apos;s interface does not calculate or alter it.</p>
        )}
        {view.kind !== "verdict" && <p className="decision__sub">{view.explanation}</p>}
      </header>
      {view.kind !== "unreadable" && <Details details={view.details} uncertified={view.kind === "uncertified"} />}
      {scenarioLabel === null ? (
        <p className="mock-note">
          Returned by the FinGuard engine running on this computer for the inputs you entered, and shown unchanged. This is a local
          prototype, not advice and not a production service.
        </p>
      ) : (
        <p className="mock-note">
          Sample result for the mock scenario “{scenarioLabel}”. It was chosen in the scenario control, not computed from the
          inputs you entered.
        </p>
      )}
    </article>
  );
}

function Details({ details, uncertified }: { details: DecisionDetails; uncertified: boolean }) {
  const c = details.candidate;
  return (
    <div className="decision__body">
      <section aria-labelledby="sel-h" className="block">
        <h3 id="sel-h">{uncertified ? "Selected option" : "Option the engine selected"}</h3>
        {c === null ? (
          <p className="muted">The engine did not select an option.</p>
        ) : (
          <>
            <dl className="facts">
              <div>
                <dt>Approach</dt>
                <dd>{c.typeLabel}</dd>
              </div>
              {c.optionId !== null && (
                <div>
                  <dt>Option</dt>
                  <dd>
                    <code>{c.optionId}</code>
                  </dd>
                </div>
              )}
              <div>
                <dt>Total cost</dt>
                <dd className="num">{c.totalCost}</dd>
              </div>
              {c.firstPayment !== null && (
                <div>
                  <dt>First payment</dt>
                  <dd>{c.firstPayment}</dd>
                </div>
              )}
              {c.finalPayment !== null && (
                <div>
                  <dt>Final payment</dt>
                  <dd>{c.finalPayment}</dd>
                </div>
              )}
            </dl>
            {c.schedule.length > 0 && (
              <div className="table-scroll">
                <table>
                  <caption>Payment schedule</caption>
                  <thead>
                    <tr>
                      <th scope="col">Due</th>
                      <th scope="col" className="num">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {c.schedule.map((s, i) => (
                      <tr key={`${s.date}-${i}`}>
                        <th scope="row">{s.date}</th>
                        <td className="num">{s.amount}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {c.spendingChanges.length > 0 && (
              <>
                <h4>Spending changes the engine listed</h4>
                <ul className="plain">
                  {c.spendingChanges.map((s, i) => (
                    <li key={`${s.category}-${i}`}>
                      {s.action} · {s.category} · <span className="num">{s.amount}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}
            {c.reasons.length > 0 && <ReasonList title="Reasons for this option" items={c.reasons} empty="" headingLevel={4} />}
          </>
        )}
      </section>

      <section aria-labelledby="why-h" className="block">
        <h3 id="why-h" className="sr-only">
          Reasons, assumptions and issues
        </h3>
        <ReasonList title="Reasons" items={details.reasons} empty="The engine listed no overall reasons." />
        <ReasonList title="Assumptions" items={details.assumptions} empty="No assumptions reported." />
        <ReasonList title="Data issues" items={details.issues} empty="No data issues reported." />
      </section>

      <section aria-labelledby="miss-h" className="block">
        <h3 id="miss-h">Missing information</h3>
        {details.missing.length === 0 ? (
          <p className="muted">The engine reported nothing missing.</p>
        ) : (
          <ul className="reason-list">
            {details.missing.map((m, i) => (
              <li key={`${m.field}-${i}`} className="reason">
                <div className="reason__top">
                  <span className="field-name">{m.field}</span>
                  <span className="chip chip--info">{m.impact}</span>
                </div>
                <p className="reason__text">
                  <code>{m.reason.code}</code> · {m.reason.text}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="meta-h" className="block">
        <h3 id="meta-h">Data quality and dates</h3>
        <dl className="facts">
          <div>
            <dt>Data quality</dt>
            <dd>{details.dataQuality}</dd>
          </div>
          <div>
            <dt>Earliest safe full payment</dt>
            <dd>{details.earliestFullPayment ?? "Not reported"}</dd>
          </div>
          <div>
            <dt>Certifiable window</dt>
            <dd>{details.window}</dd>
          </div>
        </dl>
        <details className="disclosure">
          <summary>Audit details</summary>
          <dl className="facts facts--stack">
            <div>
              <dt>Engine version</dt>
              <dd>
                <code>{details.engineVersion}</code>
              </dd>
            </div>
            <div>
              <dt>Input hash</dt>
              <dd>
                <code className="hash">{details.inputHash}</code>
              </dd>
            </div>
            <div>
              <dt>Result hash</dt>
              <dd>
                <code className="hash">{details.resultHash}</code>
              </dd>
            </div>
          </dl>
        </details>
      </section>
    </div>
  );
}
