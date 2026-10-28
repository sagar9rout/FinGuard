/**
 * Mock adapter: returns committed SYNTHETIC sample responses (src/fixtures/engineSamples.ts).
 *
 * Important property: the returned result does NOT depend on the request's amounts. The scenario is chosen
 * explicitly (by the "Mock engine scenario" control), so nothing here can be mistaken for, or behave like, an
 * affordability calculation. The request is accepted only to honour the adapter interface.
 */
import {
  affordableLaterResponse,
  affordableNowResponse,
  affordableWithPlanResponse,
  dashboardForecast,
  dashboardRequest,
  generalErrorResponse,
  notAffordableResponse,
  uncertifiedResponse,
  validationErrorResponse,
} from "../fixtures/engineSamples.ts";
import type { AnalysisRequest, AnalyzeResponse, ApiErrorResponse } from "../types/api.ts";
import type { AdapterError, AnalysisAdapter, AnalyzeResult, DashboardResult } from "./analysisAdapter.ts";

export const SCENARIOS = [
  { key: "affordable_now", label: "Affordable now" },
  { key: "affordable_with_plan", label: "Affordable with a plan" },
  { key: "affordable_later", label: "Affordable later" },
  { key: "not_affordable", label: "Not affordable" },
  { key: "uncertified", label: "Could not be certified" },
  { key: "validation_error", label: "API validation error (422)" },
  { key: "general_error", label: "General error (500)" },
  { key: "empty", label: "Empty (no result returned)" },
] as const;
export type ScenarioKey = (typeof SCENARIOS)[number]["key"];

export const DASHBOARD_STATES = [
  { key: "ready", label: "Sample forecast" },
  { key: "empty", label: "Empty (no forecast data)" },
  { key: "error", label: "General error (500)" },
] as const;
export type DashboardStateKey = (typeof DASHBOARD_STATES)[number]["key"];

const SUCCESS: Readonly<Record<"affordable_now" | "affordable_with_plan" | "affordable_later" | "not_affordable" | "uncertified", AnalyzeResponse>> = {
  affordable_now: affordableNowResponse,
  affordable_with_plan: affordableWithPlanResponse,
  affordable_later: affordableLaterResponse,
  not_affordable: notAffordableResponse,
  uncertified: uncertifiedResponse,
};

function toError(e: ApiErrorResponse): AdapterError {
  return { status: e.status, code: e.body.error.code, violations: e.body.error.violations ?? [] };
}

export interface MockAdapterOptions {
  readonly latencyMs?: number;
  readonly scenario?: ScenarioKey;
  readonly dashboard?: DashboardStateKey;
}

export class MockAdapter implements AnalysisAdapter {
  readonly kind = "mock" as const;
  scenario: ScenarioKey;
  dashboardState: DashboardStateKey;
  private readonly latencyMs: number;

  constructor(options: MockAdapterOptions = {}) {
    this.latencyMs = options.latencyMs ?? 400;
    this.scenario = options.scenario ?? "affordable_now";
    this.dashboardState = options.dashboard ?? "ready";
  }

  private wait(): Promise<void> {
    return this.latencyMs <= 0 ? Promise.resolve() : new Promise((resolve) => setTimeout(resolve, this.latencyMs));
  }

  async analyze(_request: AnalysisRequest): Promise<AnalyzeResult> {
    await this.wait();
    const key = this.scenario;
    if (key === "validation_error") return { ok: false, error: toError(validationErrorResponse) };
    if (key === "general_error") return { ok: false, error: toError(generalErrorResponse) };
    if (key === "empty") return { ok: true, empty: true };
    return { ok: true, response: SUCCESS[key] };
  }

  async loadDashboard(): Promise<DashboardResult> {
    await this.wait();
    if (this.dashboardState === "error") return { ok: false, error: toError(generalErrorResponse) };
    const p = dashboardRequest.profile;
    const forecast =
      this.dashboardState === "empty"
        ? { ...dashboardForecast, result: { ...dashboardForecast.result, baseline_series: [] } }
        : dashboardForecast;
    return {
      ok: true,
      profile: {
        homeCurrency: p.home_currency,
        balance: p.current_available_balance,
        reserve: p.minimum_balance_to_keep,
        balanceAsOf: p.balance_as_of ?? null,
      },
      forecast,
    };
  }
}
