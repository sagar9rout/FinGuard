import assert from "node:assert/strict";
import { test } from "node:test";
import { classifyError } from "../../src/lib/errorKind.ts";

const e = (status: number, code: string) => ({ status, code, violations: [] });

test("validation, unavailable and unexpected failures are told apart", () => {
  assert.equal(classifyError(e(422, "invalid_request")), "validation");
  assert.equal(classifyError(e(400, "invalid_json")), "validation");
  assert.equal(classifyError(e(0, "network_error")), "unavailable");
  assert.equal(classifyError(e(0, "timeout")), "unavailable");
  assert.equal(classifyError(e(503, "engine_unavailable")), "unavailable");
  assert.equal(classifyError(e(500, "internal_error")), "unexpected");
  assert.equal(classifyError(e(200, "invalid_response")), "unexpected");
});
