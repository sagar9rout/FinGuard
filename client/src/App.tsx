import { useMemo, useState } from "react";
import { selectAdapter, type Selection } from "./adapters/selectAdapter.ts";
import { AppShell, type View } from "./components/layout/AppShell.tsx";
import { useAnalysis } from "./hooks/useAnalysis.ts";
import { useDashboard } from "./hooks/useDashboard.ts";
import type { RuntimeConfig } from "./lib/runtime.ts";
import { AnalysePage } from "./pages/AnalysePage.tsx";
import { OverviewPage } from "./pages/OverviewPage.tsx";

/**
 * Composition root. The mode ("mock", "live" or a configuration error) arrives as a prop from main.tsx, which reads it
 * from the build environment; the adapter is chosen once by selectAdapter. State is kept here (in memory) so it
 * survives switching between pages; nothing is persisted.
 */
export function App({ runtime }: { readonly runtime: RuntimeConfig }) {
  const selection = useMemo(() => selectAdapter(runtime), [runtime]);
  if (selection.mode === "misconfigured") return <ConfigError reason={selection.reason} />;
  return <Workspace selection={selection} />;
}

function ConfigError({ reason }: { readonly reason: string }) {
  return (
    <AppShell mode="misconfigured" view="overview" onView={() => undefined}>
      <div className="page">
        <div className="notice notice--error" role="alert">
          <h2>FinGuard is not configured</h2>
          <p>{reason}</p>
          <p className="muted small">Fix the client environment (see client/.env.example) and restart. No request has been made.</p>
        </div>
      </div>
    </AppShell>
  );
}

function Workspace({ selection }: { readonly selection: Exclude<Selection, { mode: "misconfigured" }> }) {
  const { adapter, mode } = selection;
  const [view, setView] = useState<View>("overview");
  const dashboard = useDashboard(adapter);
  const analysis = useAnalysis(adapter);

  return (
    <AppShell mode={mode} {...(selection.mode === "live" ? { apiOrigin: selection.origin } : {})} view={view} onView={setView}>
      {view === "overview" ? (
        <OverviewPage
          state={dashboard.state}
          mode={mode}
          mockState={dashboard.mockState}
          onMockState={dashboard.setMockState}
          onRetry={dashboard.retry}
          onAnalyse={() => setView("analyse")}
        />
      ) : (
        <AnalysePage analysis={analysis} mode={mode} />
      )}
    </AppShell>
  );
}
