import assert from "node:assert/strict";
import { test } from "node:test";
import { LiveAdapter } from "../../src/adapters/liveAdapter.ts";
import { affordableNowResponse, dashboardForecast, dashboardRequest, uncertifiedResponse, validationErrorResponse } from "../../src/fixtures/engineSamples.ts";
import { buildDecisionView } from "../../src/lib/decision.ts";
import { sampleForm, toRequest } from "../../src/lib/form.ts";

const ORIGIN = "http://127.0.0.1:8000";
const request = toRequest(sampleForm());

interface Call {
  readonly url: string;
  readonly init: RequestInit;
}
function stub(respond: (call: Call) => Response | Promise<Response>) {
  const calls: Call[] = [];
  const fetchImpl = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const call = { url: String(input), init: init ?? {} };
    calls.push(call);
    return respond(call);
  }) as typeof fetch;
  return { calls, adapter: new LiveAdapter(ORIGIN, { fetchImpl, timeoutMs: 200 }) };
}
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

test("analyze POSTs the request body to /v1/analyze on the configured origin only, without credentials", async () => {
  const { adapter, calls } = stub(() => json(affordableNowResponse));
  const r = await adapter.analyze(request);
  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.url, `${ORIGIN}/v1/analyze`);
  assert.equal(calls[0]?.init.method, "POST");
  assert.equal(calls[0]?.init.credentials, "omit");
  assert.equal(calls[0]?.init.referrerPolicy, "no-referrer");
  assert.deepEqual(JSON.parse(String(calls[0]?.init.body)), request);
  assert.ok(r.ok && "response" in r);
  if (r.ok && "response" in r) assert.deepEqual(r.response, affordableNowResponse);
});

test("money stays a decimal string on the wire and in the response", async () => {
  const { adapter, calls } = stub(() => json(affordableNowResponse));
  await adapter.analyze(request);
  const sent = JSON.parse(String(calls[0]?.init.body)) as typeof request;
  assert.equal(typeof sent.purchase.amount, "string");
  assert.equal(sent.purchase.amount, request.purchase.amount);
  assert.match(String(calls[0]?.init.body), /"amount":"/);
});

test("an uncertified response is passed through unchanged and still reads as not certified", async () => {
  const { adapter } = stub(() => json(uncertifiedResponse));
  const r = await adapter.analyze(request);
  assert.ok(r.ok && "response" in r);
  if (r.ok && "response" in r) {
    assert.deepEqual(r.response, uncertifiedResponse);
    assert.equal(r.response.outcome.certified, false);
    assert.equal(r.response.outcome.status, null);
    assert.equal(buildDecisionView(r.response, "ZAR").kind, "uncertified");
  }
});

test("422 and 500 documented error bodies map to AdapterError with code and violations", async () => {
  const v = stub(() => json(validationErrorResponse.body, 422));
  const r = await v.adapter.analyze(request);
  assert.ok(!r.ok);
  if (!r.ok) {
    assert.equal(r.error.status, 422);
    assert.equal(r.error.code, validationErrorResponse.body.error.code);
    assert.deepEqual(r.error.violations, validationErrorResponse.body.error.violations ?? []);
  }
  const g = stub(() => json({ error: { code: "internal_error" } }, 500));
  const e = await g.adapter.analyze(request);
  assert.ok(!e.ok);
  if (!e.ok) assert.deepEqual(e.error, { status: 500, code: "internal_error", violations: [] });
  const u = stub(() => json({ error: { code: "engine_unavailable" } }, 503));
  const x = await u.adapter.analyze(request);
  assert.ok(!x.ok && x.error.status === 503 && x.error.code === "engine_unavailable");
});

test("a non-JSON or unexpected error body is reported without guessing", async () => {
  const html = stub(() => new Response("<html>Bad Gateway</html>", { status: 502 }));
  const a = await html.adapter.analyze(request);
  assert.ok(!a.ok && a.error.status === 502 && a.error.code === "http_error" && a.error.violations.length === 0);
  const odd = stub(() => json({ message: "nope" }, 400));
  const b = await odd.adapter.analyze(request);
  assert.ok(!b.ok && b.error.code === "http_error");
});

test("a 200 that is not JSON or lacks the envelope is invalid_response, never a verdict", async () => {
  for (const respond of [() => new Response("not json", { status: 200 }), () => json({ hello: 1 }), () => json([1, 2]), () => json({ outcome: { certified: true }, result: 5 })]) {
    const { adapter } = stub(respond);
    const r = await adapter.analyze(request);
    assert.ok(!r.ok && r.error.code === "invalid_response" && r.error.status === 200);
  }
});

test("network failure (refused connection, CORS or CSP block) maps to network_error with status 0", async () => {
  const { adapter } = stub(() => {
    throw new TypeError("Failed to fetch");
  });
  const r = await adapter.analyze(request);
  assert.ok(!r.ok);
  if (!r.ok) assert.deepEqual(r.error, { status: 0, code: "network_error", violations: [] });
  const d = await adapter.loadDashboard();
  assert.ok(!d.ok && d.error.code === "network_error");
});

test("a request that never completes times out", async () => {
  const { adapter } = stub(
    (call) =>
      new Promise<Response>((_, reject) => {
        call.init.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
      }),
  );
  const r = await adapter.analyze(request);
  assert.ok(!r.ok && r.error.code === "timeout" && r.error.status === 0);
});

test("loadDashboard forecasts the synthetic profile via /v1/forecast and derives the profile from that request", async () => {
  const { adapter, calls } = stub(() => json(dashboardForecast));
  const d = await adapter.loadDashboard();
  assert.equal(calls[0]?.url, `${ORIGIN}/v1/forecast`);
  assert.deepEqual(JSON.parse(String(calls[0]?.init.body)), dashboardRequest);
  assert.ok(d.ok);
  if (d.ok) {
    assert.deepEqual(d.forecast, dashboardForecast);
    assert.equal(d.profile.balance, dashboardRequest.profile.current_available_balance);
    assert.equal(d.profile.reserve, dashboardRequest.profile.minimum_balance_to_keep);
  }
});

test("the other documented endpoints use the documented methods and paths", async () => {
  const { adapter, calls } = stub((c) =>
    c.url.endsWith("/v1/validate") ? json({ valid: true, violations: [] }) : json({ status: "ok" }),
  );
  assert.ok((await adapter.health()).ok);
  assert.ok((await adapter.meta()).ok);
  assert.ok((await adapter.analysisRequestSchema()).ok);
  const v = await adapter.validate(request);
  assert.ok(v.ok && v.data.valid && v.data.violations.length === 0);
  assert.deepEqual(
    calls.map((c) => `${c.init.method} ${c.url.slice(ORIGIN.length)}`),
    ["GET /health", "GET /v1/meta", "GET /v1/schema/analysis-request", "POST /v1/validate"],
  );
  assert.equal(calls[0]?.init.body, undefined);
});

test("validate returns violations from a 200 and rejects a malformed validate body", async () => {
  const a = stub(() => json({ valid: false, violations: ["purchase.amount"] }));
  const r = await a.adapter.validate(request);
  assert.ok(r.ok && !r.data.valid && r.data.violations[0] === "purchase.amount");
  const b = stub(() => json({ valid: "yes" }));
  const s = await b.adapter.validate(request);
  assert.ok(!s.ok && s.error.code === "invalid_response");
});
