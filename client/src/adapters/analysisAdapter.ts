/**
 * The seam between the UI and "the engine". The UI depends only on this interface.
 *
 * Two implementations exist and the app selects one explicitly (lib/runtime.ts, adapters/selectAdapter.ts):
 *  - MockAdapter (mockAdapter.ts): committed synthetic samples, no network;
 *  - LiveAdapter (liveAdapter.ts): the documented loopback HTTP API (docs/api/v1.md), the only code that uses the network.
 */
import type { AnalysisRequest, AnalyzeResponse, ForecastResponse } from "../types/api.ts";

export interface AdapterError {
  readonly status: number;
  readonly code: string;
  readonly violations: readonly string[];
}

export type AnalyzeResult =
  | { readonly ok: true; readonly response: AnalyzeResponse }
  | { readonly ok: true; readonly empty: true }
  | { readonly ok: false; readonly error: AdapterError };

export interface DashboardProfile {
  readonly homeCurrency: string;
  readonly balance: string;
  readonly reserve: string;
  readonly balanceAsOf: string | null;
}

export type DashboardResult =
  | { readonly ok: true; readonly profile: DashboardProfile; readonly forecast: ForecastResponse }
  | { readonly ok: false; readonly error: AdapterError };

export interface AnalysisAdapter {
  /** "mock" returns committed samples; "live" calls the local API. The app banner reflects which one is active. */
  readonly kind: "mock" | "live";
  analyze(request: AnalysisRequest): Promise<AnalyzeResult>;
  loadDashboard(): Promise<DashboardResult>;
}

/** Result of a plain endpoint call. */
export type ApiResult<T> = { readonly ok: true; readonly data: T } | { readonly ok: false; readonly error: AdapterError };
