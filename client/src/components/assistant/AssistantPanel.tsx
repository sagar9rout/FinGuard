import { ASSISTANT_DISCLOSURE, missingFields, nextQuestion, summarize } from "../../lib/assistant.ts";
import type { FieldName, FormValues } from "../../lib/form.ts";

interface Props {
  readonly values: FormValues;
  readonly onFocusField: (field: FieldName) => void;
}

/**
 * A rule-based guided input collector. It is not an AI model: it reads the structured form, asks for the next
 * missing required input, and reads entered values back. It never sees or comments on a result.
 */
export function AssistantPanel({ values, onFocusField }: Props) {
  const next = nextQuestion(values);
  const missing = missingFields(values);
  const lines = summarize(values);
  return (
    <section className="assistant" aria-labelledby="assistant-h">
      <h2 id="assistant-h">Guided input helper</h2>
      <p className="assistant__disclosure">{ASSISTANT_DISCLOSURE}</p>

      <div className="bubble" aria-live="polite">
        {next === null ? (
          <p>
            All required inputs look complete. Submit the form to ask the engine. I cannot tell you what it will say, and I do not
            decide anything myself.
          </p>
        ) : (
          <>
            <p className="bubble__q">{next.question}</p>
            {next.hint !== "" && <p className="muted small">{next.hint}</p>}
            <button type="button" className="btn btn--small" onClick={() => onFocusField(next.field)}>
              Go to this field
            </button>
          </>
        )}
      </div>

      <p className="muted small">
        {missing.length === 0 ? "No required inputs outstanding." : `${missing.length} required input${missing.length === 1 ? "" : "s"} still to complete.`}
      </p>

      <h3>What you have entered</h3>
      <dl className="facts facts--stack">
        {lines.map((l) => (
          <div key={l.label}>
            <dt>{l.label}</dt>
            <dd>{l.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
