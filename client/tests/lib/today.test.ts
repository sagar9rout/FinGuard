import assert from "node:assert/strict";
import { test } from "node:test";
import { SAMPLE_AS_OF, emptyForm, sampleForm, toRequest } from "../../src/lib/form.ts";
import { defaultAsOf, isBeforeDay, localIsoDate } from "../../src/lib/today.ts";

test("localIsoDate uses the local calendar date, not UTC", () => {
  const before = process.env["TZ"];
  try {
    process.env["TZ"] = "Asia/Calcutta"; // UTC+05:30
    // 2026-10-27 19:00 UTC is 00:30 on the 28th in India; toISOString() would say the 27th.
    const instant = new Date(Date.UTC(2026, 9, 27, 19, 0, 0));
    assert.equal(instant.toISOString().slice(0, 10), "2026-10-27");
    assert.equal(localIsoDate(instant), "2026-10-28");
    process.env["TZ"] = "America/Los_Angeles"; // UTC-07:00 in October
    assert.equal(localIsoDate(new Date(Date.UTC(2026, 9, 28, 3, 0, 0))), "2026-10-27");
  } finally {
    if (before === undefined) delete process.env["TZ"];
    else process.env["TZ"] = before;
  }
});

test("localIsoDate zero-pads month and day", () => {
  assert.equal(localIsoDate(new Date(2026, 0, 5, 12, 0, 0)), "2026-01-05");
});

test("live mode defaults to today; mock mode keeps the fixed sample date", () => {
  const now = new Date(2026, 9, 28, 14, 6, 0);
  assert.equal(defaultAsOf("live", now), "2026-10-28");
  assert.equal(defaultAsOf("mock", now), SAMPLE_AS_OF);
  assert.equal(SAMPLE_AS_OF, "2026-10-24");
});

test("the form's analysis date is what is sent as as_of", () => {
  const live = sampleForm("2026-10-28");
  assert.equal(live.asOf, "2026-10-28");
  assert.equal(live.balanceAsOf, "2026-10-28");
  assert.equal(live.desiredBy, ""); // no deadline is derived or guessed for a non-fixture date
  assert.equal(toRequest(live).as_of, "2026-10-28");
  assert.equal(emptyForm("2026-10-28").asOf, "2026-10-28");
  const fixed = sampleForm();
  assert.equal(fixed.asOf, "2026-10-24");
  assert.equal(fixed.desiredBy, "2026-11-30");
});

test("isBeforeDay orders YYYY-MM-DD strings", () => {
  assert.ok(isBeforeDay("2026-10-24", "2026-10-28"));
  assert.ok(!isBeforeDay("2026-10-28", "2026-10-28"));
  assert.ok(!isBeforeDay("2027-01-01", "2026-12-31"));
});
