import assert from "node:assert/strict";
import { test } from "node:test";
import { parseApiOrigin } from "../../src/lib/apiOrigin.ts";

test("accepts loopback origins with an explicit port and normalises a trailing slash", () => {
  for (const [raw, want] of [
    ["http://127.0.0.1:8000", "http://127.0.0.1:8000"],
    ["http://localhost:8000/", "http://localhost:8000"],
    ["  http://[::1]:9000  ", "http://[::1]:9000"],
    ["http://127.0.0.1:65535", "http://127.0.0.1:65535"],
  ] as const) {
    assert.deepEqual(parseApiOrigin(raw), { ok: true, origin: want }, raw);
  }
});

test("rejects wildcards, other hosts, https, paths, userinfo, queries and bad ports", () => {
  const bad = [
    undefined,
    "",
    "*",
    "http://*",
    "http://*:8000",
    "http://example.com:8000",
    "http://0.0.0.0:8000",
    "http://127.0.0.1.evil.test:8000",
    "http://localhost.evil.test:8000",
    "https://127.0.0.1:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:0",
    "http://127.0.0.1:08000",
    "http://127.0.0.1:65536",
    "http://127.0.0.1:123456",
    "http://127.0.0.1:8000/v1",
    "http://127.0.0.1:8000?x=1",
    "http://127.0.0.1:8000#x",
    "http://user@127.0.0.1:8000",
    "http://127.0.0.1:8000 http://evil.test",
    "http://127.0.0.1:8000;",
    "null",
  ];
  for (const raw of bad) assert.equal(parseApiOrigin(raw).ok, false, String(raw));
});
