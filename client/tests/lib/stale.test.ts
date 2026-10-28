import assert from "node:assert/strict";
import { test } from "node:test";
import { sampleForm } from "../../src/lib/form.ts";
import { inputsKey, isResultStale } from "../../src/lib/stale.ts";

test("a result is stale only when the inputs changed after it was requested", () => {
  const v = sampleForm();
  const key = inputsKey(v);
  assert.equal(isResultStale(true, key, v), false);
  assert.equal(isResultStale(true, key, { ...v, purchaseAmount: "27001" }), true);
  assert.equal(isResultStale(true, key, { ...v, asOf: "2026-10-28" }), true);
  assert.equal(isResultStale(false, key, { ...v, purchaseAmount: "1" }), false);
  assert.equal(isResultStale(true, null, v), false);
});
