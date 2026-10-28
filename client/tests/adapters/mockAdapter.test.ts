import assert from "node:assert/strict";
import { test } from "node:test";
import { MockAdapter, SCENARIOS } from "../../src/adapters/mockAdapter.ts";
import { emptyForm, sampleForm, toRequest } from "../../src/lib/form.ts";

const request = toRequest(sampleForm());

test("each scenario returns its committed sample and is independent of the request amounts", async () => {
  const a = new MockAdapter({ latencyMs: 0 });
  const huge = toRequest({ ...sampleForm(), purchaseAmount: "999999999" });
  for (const s of SCENARIOS) {
    a.scenario = s.key;
    const r1 = await a.analyze(request);
    const r2 = await a.analyze(huge);
    assert.deepEqual(r1, r2, `${s.key} must not depend on the request`);
  }
});

test("scenario -> outcome mapping for the four statuses plus uncertified", async () => {
  const a = new MockAdapter({ latencyMs: 0 });
  const expect: Record<string, [boolean, string | null]> = {
    affordable_now: [true, "affordable_now"],
    affordable_with_plan: [true, "affordable_with_plan"],
    affordable_later: [true, "affordable_later"],
    not_affordable: [true, "not_affordable"],
    uncertified: [false, null],
  };
  for (const [key, [certified, status]] of Object.entries(expect)) {
    a.scenario = key as (typeof SCENARIOS)[number]["key"];
    const r = await a.analyze(request);
    assert.ok(r.ok && "response" in r, key);
    if (r.ok && "response" in r) {
      assert.equal(r.response.outcome.certified, certified, key);
      assert.equal(r.response.outcome.status, status, key);
    }
  }
});

test("validation and general errors use the documented error body shape", async () => {
  const a = new MockAdapter({ latencyMs: 0 });
  a.scenario = "validation_error";
  const v = await a.analyze(request);
  assert.ok(!v.ok);
  if (!v.ok) {
    assert.equal(v.error.status, 422);
    assert.equal(v.error.code, "invalid_request");
    assert.ok(v.error.violations.length > 0);
  }
  a.scenario = "general_error";
  const g = await a.analyze(request);
  assert.ok(!g.ok);
  if (!g.ok) {
    assert.equal(g.error.status, 500);
    assert.equal(g.error.code, "internal_error");
    assert.deepEqual(g.error.violations, []);
  }
});

test("the empty scenario returns an explicit empty result", async () => {
  const a = new MockAdapter({ latencyMs: 0, scenario: "empty" });
  const r = await a.analyze(request);
  assert.deepEqual(r, { ok: true, empty: true });
});

test("the dashboard adapter returns the documented baseline series, an empty one, or an error", async () => {
  const a = new MockAdapter({ latencyMs: 0 });
  const ready = await a.loadDashboard();
  assert.ok(ready.ok);
  if (ready.ok) {
    assert.ok(ready.forecast.result.baseline_series.length > 0);
    assert.equal(ready.profile.homeCurrency, "INR");
  }
  a.dashboardState = "empty";
  const empty = await a.loadDashboard();
  assert.ok(empty.ok && empty.forecast.result.baseline_series.length === 0);
  a.dashboardState = "error";
  assert.ok(!(await a.loadDashboard()).ok);
});

test("the mock adapter declares itself a mock", () => {
  assert.equal(new MockAdapter().kind, "mock");
  assert.equal(emptyForm().balance, "");
});
