/**
 * Live adapter: the six documented endpoints of the loopback API (docs/api/v1.md, server/README.md).
 *
 * It forwards the request exactly as built by `toRequest` (money stays a decimal string) and returns the response
 * body unchanged. It computes nothing, never reads money as a number, never logs or stores a request or response, and
 * only ever talks to the one validated loopback origin it was constructed with. Failures become `AdapterError`s:
 *  - HTTP errors keep the documented `{error:{code,violations?}}` body fields and the real status;
 *  - `network_error` / `timeout` (status 0): the server could not be reached or did not answer in time;
 *  - `invalid_response`: a success status whose body is not the documented shape.
 */
import type { AnalysisRequest, AnalyzeResponse, ForecastResponse } from "../types/api.ts";
import { dashboardRequest } from "../fixtures/engineSamples.ts";
import { parseApiOrigin } from "../lib/apiOrigin.ts";
import type { AdapterError, AnalysisAdapter, AnalyzeResult, ApiResult, DashboardResult } from "./analysisAdapter.ts";

export interface ValidateResponse {
  readonly valid: boolean;
  readonly violations: readonly string[];
}
export type JsonObject = Readonly<Record<string, unknown>>;

export interface LiveAdapterOptions {
  /** Injected for tests; defaults to the browser's fetch. */
  readonly fetchImpl?: typeof fetch;
  readonly timeoutMs?: number;
  /** The synthetic request used for the overview forecast. Defaults to the committed synthetic sample. */
  readonly overviewRequest?: AnalysisRequest;
}

const DEFAULT_TIMEOUT_MS = 15_000;

function isObject(v: unknown): v is JsonObject {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}
const fail = (status: number, code: string, violations: readonly string[] = []): { ok: false; error: AdapterError } => ({
  ok: false,
  error: { status, code, violations },
});

/** Documented error body -> AdapterError; anything else keeps the status with a generic code. */
function errorFromBody(status: number, body: unknown): AdapterError {
  if (isObject(body) && isObject(body["error"]) && typeof body["error"]["code"] === "string") {
    const v = body["error"]["violations"];
    const violations = Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
    return { status, code: body["error"]["code"], violations };
  }
  return { status, code: "http_error", violations: [] };
}

export class LiveAdapter implements AnalysisAdapter {
  readonly kind = "live" as const;
  readonly origin: string;
  private readonly fetchImpl: typeof fetch;
  private readonly timeoutMs: number;
  private readonly overviewRequest: AnalysisRequest;

  constructor(apiOrigin: string, options: LiveAdapterOptions = {}) {
    const parsed = parseApiOrigin(apiOrigin);
    if (!parsed.ok) throw new Error(parsed.reason);
    this.origin = parsed.origin;
    this.fetchImpl = options.fetchImpl ?? ((input, init) => globalThis.fetch(input, init));
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.overviewRequest = options.overviewRequest ?? dashboardRequest;
  }

  private async call(method: "GET" | "POST", path: string, body?: unknown): Promise<ApiResult<unknown>> {
    const controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, this.timeoutMs);
    try {
      const init: RequestInit = {
        method,
        mode: "cors",
        credentials: "omit",
        cache: "no-store",
        referrerPolicy: "no-referrer",
        signal: controller.signal,
        headers: { Accept: "application/json", ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      };
      const res = await this.fetchImpl(`${this.origin}${path}`, init);
      const text = await res.text();
      let parsed: unknown;
      try {
        parsed = JSON.parse(text);
      } catch {
        return res.ok ? fail(res.status, "invalid_response") : fail(res.status, "http_error");
      }
      if (!res.ok) return { ok: false, error: errorFromBody(res.status, parsed) };
      return { ok: true, data: parsed };
    } catch {
      return timedOut ? fail(0, "timeout") : fail(0, "network_error");
    } finally {
      clearTimeout(timer);
    }
  }

  private async object(method: "GET" | "POST", path: string, body?: unknown): Promise<ApiResult<JsonObject>> {
    const r = await this.call(method, path, body);
    if (!r.ok) return r;
    return isObject(r.data) ? { ok: true, data: r.data } : fail(200, "invalid_response");
  }

  /** GET /health: liveness only. */
  async health(): Promise<ApiResult<JsonObject>> {
    return this.object("GET", "/health");
  }
  /** GET /v1/meta */
  async meta(): Promise<ApiResult<JsonObject>> {
    return this.object("GET", "/v1/meta");
  }
  /** GET /v1/schema/analysis-request */
  async analysisRequestSchema(): Promise<ApiResult<JsonObject>> {
    return this.object("GET", "/v1/schema/analysis-request");
  }
  /** POST /v1/validate: always 200 with `valid` and `violations`. */
  async validate(request: AnalysisRequest): Promise<ApiResult<ValidateResponse>> {
    const r = await this.object("POST", "/v1/validate", request);
    if (!r.ok) return r;
    const v = r.data["violations"];
    if (typeof r.data["valid"] !== "boolean" || !Array.isArray(v)) return fail(200, "invalid_response");
    return { ok: true, data: { valid: r.data["valid"], violations: v.filter((x): x is string => typeof x === "string") } };
  }
  /** POST /v1/forecast: baseline forecast, no decision. */
  async forecast(request: AnalysisRequest): Promise<ApiResult<ForecastResponse>> {
    const r = await this.object("POST", "/v1/forecast", request);
    if (!r.ok) return r;
    return isObject(r.data["result"]) ? { ok: true, data: r.data as unknown as ForecastResponse } : fail(200, "invalid_response");
  }

  /** POST /v1/analyze. The body is returned unchanged; `buildDecisionView` reads `outcome.certified` first. */
  async analyze(request: AnalysisRequest): Promise<AnalyzeResult> {
    const r = await this.object("POST", "/v1/analyze", request);
    if (!r.ok) return r;
    if (!isObject(r.data["outcome"]) || !isObject(r.data["result"])) return fail(200, "invalid_response");
    return { ok: true, response: r.data as unknown as AnalyzeResponse };
  }

  /** Overview: the committed SYNTHETIC profile is sent to /v1/forecast; the engine's baseline is shown as received. */
  async loadDashboard(): Promise<DashboardResult> {
    const r = await this.forecast(this.overviewRequest);
    if (!r.ok) return r;
    const p = this.overviewRequest.profile;
    return {
      ok: true,
      profile: {
        homeCurrency: p.home_currency,
        balance: p.current_available_balance,
        reserve: p.minimum_balance_to_keep,
        balanceAsOf: p.balance_as_of ?? null,
      },
      forecast: r.data,
    };
  }
}
