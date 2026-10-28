import assert from "node:assert/strict";
import { test } from "node:test";
import { buildDecisionView, STATUS_LABEL, UNCERTIFIED_EXPLANATION } from "../../src/lib/decision.ts";
import type { AnalyzeResponse } from "../../src/types/api.ts";
import {
  affordableLaterResponse,
  affordableNowResponse,
  affordableWithPlanResponse,
  notAffordableResponse,
  uncertifiedResponse,
} from "../../src/fixtures/engineSamples.ts";

function clone(r: AnalyzeResponse): AnalyzeResponse {
  return structuredClone(r) as AnalyzeResponse;
}

test("each certified fixture maps to its own documented label", () => {
  const cases: [AnalyzeResponse, string][] = [
    [affordableNowResponse, "Affordable now"],
    [affordableWithPlanResponse, "Affordable with a plan"],
    [affordableLaterResponse, "Affordable later"],
    [notAffordableResponse, "Not affordable"],
  ];
  for (const [response, label] of cases) {
    const v = buildDecisionView(response, "INR");
    assert.equal(v.kind, "verdict");
    assert.equal(v.headline, label);
  }
  assert.deepEqual(Object.values(STATUS_LABEL).sort(), ["Affordable later", "Affordable now", "Affordable with a plan", "Not affordable"]);
});

test("certified=false is 'could not be certified', never 'not affordable'", () => {
  const v = buildDecisionView(uncertifiedResponse, "INR");
  assert.equal(v.kind, "uncertified");
  assert.equal(v.headline, "Could not be certified");
  assert.notEqual(v.headline, STATUS_LABEL.not_affordable);
  assert.equal(v.kind === "uncertified" && v.explanation, UNCERTIFIED_EXPLANATION);
  assert.match(UNCERTIFIED_EXPLANATION, /not the same as/);
});

test("the real uncertified fixture really has certified=false and a null status", () => {
  assert.equal(uncertifiedResponse.outcome.certified, false);
  assert.equal(uncertifiedResponse.outcome.status, null);
  assert.equal(uncertifiedResponse.result.status, null);
});

test("an uncertified response is never rendered as a verdict even if a status leaks in", () => {
  for (const leaked of ["not_affordable", "affordable_now"]) {
    const r = clone(uncertifiedResponse) as { outcome: { certified: boolean; status: string | null }; result: { status: string | null } };
    r.outcome.status = leaked;
    r.result.status = leaked;
    const v = buildDecisionView(r as unknown as AnalyzeResponse, "INR");
    assert.equal(v.kind, "uncertified", leaked);
    assert.ok(!JSON.stringify(v).includes("Not affordable"), leaked);
    assert.ok(!JSON.stringify(v).includes("Affordable now"), leaked);
  }
});

test("the uncertified view still lists the engine's blocking reason with its documented copy", () => {
  const v = buildDecisionView(uncertifiedResponse, "INR");
  assert.equal(v.kind, "uncertified");
  if (v.kind !== "uncertified") return;
  const blocking = v.details.reasons.find((r) => r.code === "UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION");
  assert.ok(blocking);
  assert.equal(blocking.severity, "blocking");
  assert.equal(blocking.mapped, true);
});

test("an unknown status on a certified response is unreadable, not guessed", () => {
  const r = clone(affordableNowResponse) as { outcome: { status: string | null }; result: { status: string | null } };
  r.outcome.status = "maybe";
  r.result.status = "maybe";
  assert.equal(buildDecisionView(r as unknown as AnalyzeResponse, "INR").kind, "unreadable");
});

test("certified but no status is unreadable", () => {
  const r = clone(affordableNowResponse) as { outcome: { status: string | null } };
  r.outcome.status = null;
  assert.equal(buildDecisionView(r as unknown as AnalyzeResponse, "INR").kind, "unreadable");
});

test("envelope and result disagreeing about certification is unreadable", () => {
  const r = clone(affordableNowResponse) as { result: { certified: boolean } };
  r.result.certified = false;
  assert.equal(buildDecisionView(r as unknown as AnalyzeResponse, "INR").kind, "unreadable");
});

test("envelope and result disagreeing about status is unreadable", () => {
  const r = clone(affordableNowResponse) as { result: { status: string | null } };
  r.result.status = "not_affordable";
  assert.equal(buildDecisionView(r as unknown as AnalyzeResponse, "INR").kind, "unreadable");
});

test("a missing or non-boolean certified flag is unreadable", () => {
  assert.equal(buildDecisionView({} as unknown as AnalyzeResponse, "INR").kind, "unreadable");
  const r = clone(affordableNowResponse) as { outcome: { certified: unknown } };
  r.outcome.certified = "true";
  assert.equal(buildDecisionView(r as unknown as AnalyzeResponse, "INR").kind, "unreadable");
});

test("details are re-formatted engine values: chosen candidate, dates, money, assumptions", () => {
  const v = buildDecisionView(affordableLaterResponse, "INR");
  assert.equal(v.kind, "verdict");
  if (v.kind !== "verdict") return;
  assert.equal(v.details.candidate?.typeLabel, "Wait, then pay in full");
  assert.equal(v.details.candidate?.totalCost, "INR 25,000.00");
  assert.equal(v.details.earliestFullPayment, "6 Nov 2026");
  assert.equal(v.details.dataQuality, "High");
  assert.ok(v.details.assumptions.some((a) => a.code === "SCHEDULED_INCOME_COUNTED"));
  assert.equal(v.details.engineVersion, affordableLaterResponse.engine_version);
});

test("not affordable has no chosen candidate and says so by omission (null), not by invention", () => {
  const v = buildDecisionView(notAffordableResponse, "INR");
  assert.equal(v.kind === "verdict" && v.details.candidate, null);
});
