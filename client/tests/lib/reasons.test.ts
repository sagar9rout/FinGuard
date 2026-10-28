import assert from "node:assert/strict";
import { test } from "node:test";
import { describeParam, describeReason, FALLBACK_COPY } from "../../src/lib/reasons.ts";
import { REASON_COPY } from "../../src/lib/reasonCopyData.ts";
import type { ReasonEntry } from "../../src/types/api.ts";

const NB = " ";

test("a documented code gets the documented copy verbatim", () => {
  const v = describeReason({ code: "PLAN_SAFE_WAIT", severity: "info", params: [] }, "INR");
  assert.equal(v.mapped, true);
  assert.equal(v.text, "A later full payment is safe");
  assert.equal(v.category, "reason");
});

test("an undocumented code gets the neutral fallback and keeps its code", () => {
  const v = describeReason({ code: "SOMETHING_NEW", severity: "info", params: [] }, "INR");
  assert.equal(v.mapped, false);
  assert.equal(v.text, FALLBACK_COPY);
  assert.equal(v.code, "SOMETHING_NEW");
  assert.equal(v.category, "unmapped");
});

test("codes the engine can emit but the document omits fall back, not guess", () => {
  for (const code of ["OBLIGATION_BEFORE_INCOME", "INCOME_ARRIVES_LATER"]) {
    assert.equal(describeReason({ code, severity: "info", params: [] }, "INR").mapped, false, code);
  }
});

test("inherited object keys are never mistaken for documented codes", () => {
  for (const code of ["constructor", "toString", "__proto__", "hasOwnProperty"]) {
    assert.equal(describeReason({ code, severity: "info", params: [] }, "INR").mapped, false, code);
  }
});

test("params stay structured: known money keys are formatted, dates formatted, others verbatim", () => {
  const entry: ReasonEntry = {
    code: "RESERVE_BREACH_IF_PAID_NOW",
    severity: "warn",
    params: [
      ["cause", "purchase_causes"],
      ["date", "2026-10-24"],
      ["shortfall", "10000.00"],
    ],
  };
  const v = describeReason(entry, "INR");
  assert.deepEqual(
    v.params.map((p) => [p.key, p.value, p.kind]),
    [
      ["cause", "purchase_causes", "text"],
      ["date", "24 Oct 2026", "date"],
      ["shortfall", `INR${NB}10,000.00`, "money"],
    ],
  );
  assert.equal(v.severity, "warn");
});

test("a money-named param with a non-decimal value is shown verbatim, not formatted", () => {
  const p = describeParam("balance", "about 5", "INR");
  assert.equal(p.kind, "text");
  assert.equal(p.value, "about 5");
});

test("unknown severities are labelled unknown, not coerced", () => {
  assert.equal(describeReason({ code: "PAY_NOW_SAFE", severity: "catastrophic", params: [] }, "INR").severity, "unknown");
});

test("every documented code has non-empty copy and a category", () => {
  const entries = Object.entries(REASON_COPY);
  assert.ok(entries.length >= 60);
  for (const [code, v] of entries) {
    assert.ok(v.copy.length > 0, code);
    assert.ok(["reason", "assumption", "issue"].includes(v.category), code);
  }
});
