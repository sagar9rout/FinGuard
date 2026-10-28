import type { AdapterError } from "../adapters/analysisAdapter.ts";

/** Which kind of failure an adapter error is, from its status and code only. Used to choose the message shown. */
export function classifyError(error: AdapterError): "validation" | "unavailable" | "unexpected" {
  if (error.status === 422 || error.status === 400) return "validation";
  if (error.status === 0 || error.status === 503 || error.code === "engine_unavailable") return "unavailable";
  return "unexpected";
}
