import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { dashboardRequest, affordableNowRequest } from "../../src/fixtures/engineSamples.ts";
import { SAMPLE_AS_OF } from "../../src/lib/form.ts";

const src = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "src");

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}

test("deterministic fixtures keep their intentionally fixed analysis date", () => {
  assert.equal(SAMPLE_AS_OF, "2026-10-24");
  assert.equal(dashboardRequest.as_of, SAMPLE_AS_OF);
  assert.equal(affordableNowRequest.as_of, SAMPLE_AS_OF);
});

test("no hard-coded calendar date outside the fixed-date fixtures and the sample-form constants", () => {
  // Dates are allowed only where they are deliberate: the committed fixtures and the mock/sample constants in form.ts.
  const allowed = new Set(["fixtures/engineSamples.ts", "lib/form.ts"]);
  const offenders: string[] = [];
  for (const file of walk(src)) {
    const rel = relative(src, file).replaceAll("\\", "/");
    if (!/\.(ts|tsx)$/.test(rel) || allowed.has(rel)) continue;
    const code = readFileSync(file, "utf8").replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`\\])\/\/.*$/gm, "$1");
    if (/\b20\d\d-\d\d-\d\d\b/.test(code)) offenders.push(rel);
  }
  assert.deepEqual(offenders, []);
});

test("live-mode code paths take the analysis date from the clock helper, not from the fixed constant", () => {
  const users = walk(src)
    .filter((f) => /\.(ts|tsx)$/.test(f))
    .filter((f) => readFileSync(f, "utf8").includes("SAMPLE_AS_OF"))
    .map((f) => relative(src, f).replaceAll("\\", "/"))
    .sort();
  // Only the constant's home, its mock/sample-form defaults and the date helper may reference it.
  assert.deepEqual(users, ["lib/form.ts", "lib/today.ts"]);
});
