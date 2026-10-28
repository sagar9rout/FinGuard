import { useRef } from "react";
import { AssistantPanel } from "../components/assistant/AssistantPanel.tsx";
import { DecisionCard } from "../components/decision/DecisionCard.tsx";
import { EmptyResultState, ErrorState, IdleState, LoadingState } from "../components/decision/ResultStates.tsx";
import { BuyOrWaitForm } from "../components/forms/BuyOrWaitForm.tsx";
import type { useAnalysis } from "../hooks/useAnalysis.ts";
import type { FieldName } from "../lib/form.ts";

function focusField(field: FieldName): void {
  document.getElementById(`field-${field}`)?.focus();
}

export function AnalysePage({ analysis, mode }: { readonly analysis: ReturnType<typeof useAnalysis>; readonly mode: "mock" | "live" }) {
  const a = analysis;
  const resultRef = useRef<HTMLDivElement>(null);

  const onSubmit = async () => {
    const valid = await a.submit(() => resultRef.current?.scrollIntoView({ block: "start" }));
    if (!valid) requestAnimationFrame(() => document.getElementById("form-errors")?.focus());
  };

  return (
    <div className="page analyse">
      <div className="analyse__form">
        <BuyOrWaitForm
          values={a.values}
          errors={a.errors}
          busy={a.busy}
          showMockControls={mode === "mock"}
          today={a.today}
          scenario={a.scenario}
          onScenario={a.setScenario}
          onChange={a.change}
          onSubmit={() => void onSubmit()}
          onSample={a.fillSample}
          onClear={a.clear}
          onFocusField={focusField}
        />
      </div>
      <div className="analyse__side">
        <AssistantPanel values={a.values} onFocusField={focusField} />
      </div>
      <div className="analyse__result" ref={resultRef}>
        {a.outcome.kind === "idle" && <IdleState />}
        {a.outcome.kind === "loading" && <LoadingState />}
        {a.outcome.kind === "empty" && <EmptyResultState />}
        {a.outcome.kind === "error" && <ErrorState error={a.outcome.error} />}
        {a.outcome.kind === "result" && <DecisionCard view={a.outcome.view} scenarioLabel={a.outcome.scenarioLabel} stale={a.stale} />}
      </div>
    </div>
  );
}
