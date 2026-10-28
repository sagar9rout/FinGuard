import assert from "node:assert/strict";
import { test } from "node:test";
import { buildDecisionView } from "../../src/lib/decision.ts";
import { STATUS_VALUES } from "../../src/types/api.ts";
import * as f from "../../src/fixtures/engineSamples.ts";

const expected = [
  [f.affordableNowResponse, "affordable_now"],
  [f.affordableWithPlanResponse, "affordable_with_plan"],
  [f.affordableLaterResponse, "affordable_later"],
  [f.notAffordableResponse, "not_affordable"],
] as const;

test("each status fixture is certified and carries exactly its own status in envelope and result", () => {
  for (const [response, status] of expected) {
    assert.equal(response.outcome.certified, true);
    assert.equal(response.result.certified, true);
    assert.equal(response.outcome.status, status);
    assert.equal(response.result.status, status);
    assert.ok((STATUS_VALUES as readonly string[]).includes(status));
    assert.equal(buildDecisionView(response, "INR").kind, "verdict");
  }
});

test("the uncertified fixture is a genuine certified=false response with a null status everywhere", () => {
  const r = f.uncertifiedResponse;
  assert.equal(r.outcome.certified, false);
  assert.equal(r.outcome.status, null);
  assert.equal(r.result.certified, false);
  assert.equal(r.result.status, null);
  assert.ok(r.result.issues.some((i) => i.code === "UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION"));
  assert.equal(buildDecisionView(r, "INR").kind, "uncertified");
});

test("all response fixtures were captured from the same engine version", () => {
  const versions = new Set([
    ...expected.map(([r]) => r.engine_version),
    f.uncertifiedResponse.engine_version,
    f.dashboardForecast.engine_version,
  ]);
  assert.equal(versions.size, 1);
});

test("money in fixtures is canonical decimal text, never a JSON number", () => {
  for (const day of f.dashboardForecast.result.baseline_series) {
    assert.equal(typeof day.low, "string");
    assert.equal(typeof day.close, "string");
  }
});
