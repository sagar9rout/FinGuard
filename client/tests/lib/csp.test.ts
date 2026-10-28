import assert from "node:assert/strict";
import { test } from "node:test";
import { buildCsp } from "../../src/lib/csp.ts";

const directives = (csp: string) => new Map(csp.split("; ").map((d) => [d.split(" ")[0] ?? "", d] as const));

test("mock mode: connect-src 'none'", () => {
  assert.equal(directives(buildCsp(null)).get("connect-src"), "connect-src 'none'");
});

test("live mode: connect-src is exactly the one validated origin", () => {
  assert.equal(directives(buildCsp("http://127.0.0.1:8000")).get("connect-src"), "connect-src http://127.0.0.1:8000");
  assert.equal(directives(buildCsp("http://localhost:8000/")).get("connect-src"), "connect-src http://localhost:8000");
});

test("every other directive is identical in both modes and stays strict", () => {
  const strip = (csp: string) => csp.split("; ").filter((d) => !d.startsWith("connect-src")).join("; ");
  assert.equal(strip(buildCsp(null)), strip(buildCsp("http://127.0.0.1:8000")));
  const csp = buildCsp("http://127.0.0.1:8000");
  for (const d of [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
  ])
    assert.ok(csp.split("; ").includes(d), d);
  assert.ok(!csp.includes("unsafe-"));
  assert.ok(!csp.includes("*"));
});

test("an invalid or non-loopback origin throws instead of widening the policy", () => {
  for (const bad of ["*", "http://example.com:8000", "https://127.0.0.1:8000", "http://127.0.0.1", "'self'", ""])
    assert.throws(() => buildCsp(bad), bad);
});
