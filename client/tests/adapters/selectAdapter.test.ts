import assert from "node:assert/strict";
import { test } from "node:test";
import { LiveAdapter } from "../../src/adapters/liveAdapter.ts";
import { MockAdapter } from "../../src/adapters/mockAdapter.ts";
import { selectAdapter } from "../../src/adapters/selectAdapter.ts";
import { resolveRuntime } from "../../src/lib/runtime.ts";

test("default configuration selects the mock adapter", () => {
  const s = selectAdapter(resolveRuntime({}));
  assert.equal(s.mode, "mock");
  assert.ok(s.mode === "mock" && s.adapter instanceof MockAdapter && s.adapter.kind === "mock");
});

test("live configuration selects the live adapter bound to the configured origin", () => {
  const s = selectAdapter(resolveRuntime({ mode: "live", apiBaseUrl: "http://127.0.0.1:8000" }));
  assert.ok(s.mode === "live");
  if (s.mode === "live") {
    assert.ok(s.adapter instanceof LiveAdapter);
    assert.equal(s.adapter.kind, "live");
    assert.equal(s.adapter.origin, "http://127.0.0.1:8000");
    assert.equal(s.origin, "http://127.0.0.1:8000");
  }
});

test("a bad configuration yields no adapter at all", () => {
  const s = selectAdapter(resolveRuntime({ mode: "live", apiBaseUrl: "http://example.com:80" }));
  assert.equal(s.mode, "misconfigured");
  assert.ok(!("adapter" in s));
});

test("the live adapter refuses a non-loopback origin directly", () => {
  assert.throws(() => new LiveAdapter("http://example.com:8000"));
  assert.throws(() => new LiveAdapter("*"));
});
