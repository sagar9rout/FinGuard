import type { DashboardStateKey } from "../adapters/mockAdapter.ts";
import { Dashboard, type DashboardState } from "../components/dashboard/Dashboard.tsx";

interface Props {
  readonly state: DashboardState;
  readonly mode: "mock" | "live";
  readonly mockState: DashboardStateKey;
  readonly onMockState: (key: DashboardStateKey) => void;
  readonly onRetry: () => void;
  readonly onAnalyse: () => void;
}

export function OverviewPage(props: Props) {
  return <Dashboard {...props} />;
}
