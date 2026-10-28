import { useEffect, useState } from "react";
import type { AnalysisAdapter } from "../adapters/analysisAdapter.ts";
import { MockAdapter, type DashboardStateKey } from "../adapters/mockAdapter.ts";
import type { DashboardState } from "../components/dashboard/Dashboard.tsx";

const CLIENT_ERROR = { status: 0, code: "client_error", violations: [] } as const;

/** Loads the overview forecast from the adapter (committed sample in mock mode, the local engine in live mode). In-memory only. */
export function useDashboard(adapter: AnalysisAdapter) {
  const [mockState, setMockState] = useState<DashboardStateKey>("ready");
  const [state, setState] = useState<DashboardState>({ kind: "loading" });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    if (adapter instanceof MockAdapter) adapter.dashboardState = mockState;
    adapter
      .loadDashboard()
      .then((r) => {
        if (cancelled) return;
        setState(r.ok ? { kind: "ready", profile: r.profile, forecast: r.forecast } : { kind: "error", error: r.error });
      })
      .catch(() => {
        if (!cancelled) setState({ kind: "error", error: CLIENT_ERROR });
      });
    return () => {
      cancelled = true;
    };
  }, [adapter, mockState, tick]);

  return { state, mockState, setMockState, retry: () => setTick((t) => t + 1) };
}
