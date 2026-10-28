import { parseApiOrigin } from "./apiOrigin.ts";

/**
 * Explicit mock-versus-live selection. `VITE_FINGUARD_MODE` is `mock` (the default when unset) or `live`.
 * Live requires `VITE_API_BASE_URL`; anything unrecognised is a configuration error, never a silent fallback to
 * either mode. The same resolution runs at build time (CSP) and in the browser (adapter choice).
 */
export type RuntimeConfig =
  | { readonly mode: "mock" }
  | { readonly mode: "live"; readonly apiOrigin: string }
  | { readonly mode: "misconfigured"; readonly reason: string };

export interface RawRuntimeEnv {
  readonly mode?: string | undefined;
  readonly apiBaseUrl?: string | undefined;
}

export function resolveRuntime(env: RawRuntimeEnv): RuntimeConfig {
  const mode = (env.mode ?? "").trim().toLowerCase();
  if (mode === "" || mode === "mock") return { mode: "mock" };
  if (mode !== "live") return { mode: "misconfigured", reason: 'VITE_FINGUARD_MODE must be "mock" or "live".' };
  const origin = parseApiOrigin(env.apiBaseUrl);
  if (!origin.ok) return { mode: "misconfigured", reason: origin.reason };
  return { mode: "live", apiOrigin: origin.origin };
}
