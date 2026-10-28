import type { ReasonView, SeverityView } from "../../lib/reasons.ts";

const SEVERITY_TEXT: Readonly<Record<SeverityView, string>> = {
  info: "Info",
  warn: "Warning",
  blocking: "Blocking",
  unknown: "Severity unknown",
};
const SEVERITY_MARK: Readonly<Record<SeverityView, string>> = { info: "●", warn: "▲", blocking: "■", unknown: "?" };

interface Props {
  readonly title: string;
  readonly items: readonly ReasonView[];
  readonly empty: string;
  readonly headingLevel?: 3 | 4;
}

/** Engine reason entries as approved copy plus structured parameters. Unmapped codes show a neutral fallback. */
export function ReasonList({ title, items, empty, headingLevel = 3 }: Props) {
  const Heading = headingLevel === 3 ? "h3" : "h4";
  return (
    <div className="reasons">
      <Heading>{title}</Heading>
      {items.length === 0 ? (
        <p className="muted">{empty}</p>
      ) : (
        <ul className="reason-list">
          {items.map((r, i) => (
            <li key={`${r.code}-${i}`} className={r.mapped ? "reason" : "reason reason--unmapped"}>
              <div className="reason__top">
                <code className="reason__code">{r.code}</code>
                <span className={`chip chip--${r.severity}`}>
                  <span aria-hidden="true">{SEVERITY_MARK[r.severity]}</span> {SEVERITY_TEXT[r.severity]}
                </span>
              </div>
              <p className="reason__text">{r.text}</p>
              {r.params.length > 0 && (
                <dl className="params">
                  {r.params.map((p) => (
                    <div key={p.key}>
                      <dt>{p.label}</dt>
                      <dd className={p.kind === "money" ? "num" : undefined}>{p.value}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
