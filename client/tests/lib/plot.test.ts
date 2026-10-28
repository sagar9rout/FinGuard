import assert from "node:assert/strict";
import { test } from "node:test";
import { buildHorizon } from "../../src/lib/plot.ts";

const dims = { width: 400, height: 200, left: 10, right: 10, top: 20, bottom: 30 };
const series = [
  { day: "2026-10-24", low: "100", close: "100" },
  { day: "2026-10-25", low: "40.50", close: "60" },
  { day: "2026-10-26", low: "70", close: "90" },
];

test("an empty series or any non-canonical value draws nothing", () => {
  assert.equal(buildHorizon([], "50", "INR", dims), null);
  assert.equal(buildHorizon([{ day: "2026-10-24", low: "1e3", close: "5" }], "50", "INR", dims), null);
  assert.equal(buildHorizon(series, "abc", "INR", dims), null);
});

test("the highest plotted value sits at the top and the lowest at the bottom, labels are the engine's own amounts", () => {
  const m = buildHorizon(series, "50", "INR", dims);
  assert.ok(m);
  assert.equal(m.maxLabel, "INR\u00a0100.00");
  assert.equal(m.minLabel, "INR\u00a040.50");
  assert.ok(m.closePath.startsWith("M10.00 20.00"));
  assert.equal(m.xLabels[0]?.text, "24 Oct 2026");
});

test("the reserve line lies between the extremes when the reserve is inside the data range", () => {
  const m = buildHorizon(series, "50", "INR", dims);
  assert.ok(m);
  const y = Number(m.reserveY);
  assert.ok(y > 20 && y < 170);
});
