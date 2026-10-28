import assert from "node:assert/strict";
import { test } from "node:test";
import { resolveRuntime } from "../../src/lib/runtime.ts";

test("mock is the default and ignores any API URL", () => {
  assert.deepEqual(resolveRuntime({}), { mode: "mock" });
  assert.deepEqual(resolveRuntime({ mode: "" }), { mode: "mock" });
  assert.deepEqual(resolveRuntime({ mode: "mock", apiBaseUrl: "http://127.0.0.1:8000" }), { mode: "mock" });
});

test("live needs a valid loopback origin", () => {
  assert.deepEqual(resolveRuntime({ mode: "live", apiBaseUrl: "http://127.0.0.1:8000/" }), { mode: "live", apiOrigin: "http://127.0.0.1:8000" });
  for (const apiBaseUrl of [undefined, "", "http://example.com:8000", "*"])
    assert.equal(resolveRuntime({ mode: "live", apiBaseUrl }).mode, "misconfigured", String(apiBaseUrl));
});

test("an unknown mode is a configuration error, not a silent fallback", () => {
  for (const mode of ["LIVE", "prod", "true", "1"]) assert.equal(resolveRuntime({ mode }).mode, "misconfigured", mode);
});
