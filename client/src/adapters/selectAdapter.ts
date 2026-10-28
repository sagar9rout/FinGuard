import type { RuntimeConfig } from "../lib/runtime.ts";
import { LiveAdapter } from "./liveAdapter.ts";
import { MockAdapter } from "./mockAdapter.ts";

export type Selection =
  | { readonly mode: "mock"; readonly adapter: MockAdapter }
  | { readonly mode: "live"; readonly adapter: LiveAdapter; readonly origin: string }
  | { readonly mode: "misconfigured"; readonly reason: string };

/** The only place an adapter is chosen. A misconfiguration selects no adapter; it never falls back to another mode. */
export function selectAdapter(config: RuntimeConfig): Selection {
  if (config.mode === "mock") return { mode: "mock", adapter: new MockAdapter() };
  if (config.mode === "live") return { mode: "live", adapter: new LiveAdapter(config.apiOrigin), origin: config.apiOrigin };
  return { mode: "misconfigured", reason: config.reason };
}
