import { parseApiOrigin } from "./apiOrigin.ts";

/**
 * The Content-Security-Policy injected into production builds. Every directive other than `connect-src` is unchanged
 * from Phase 1. `connect-src` is `'none'` for the mock build and exactly one validated loopback origin for the live
 * build; there is no wildcard and no fallback. An invalid origin throws, so a bad configuration fails the build.
 */
export function buildCsp(apiOrigin: string | null): string {
  let connect = "'none'";
  if (apiOrigin !== null) {
    const parsed = parseApiOrigin(apiOrigin);
    if (!parsed.ok) throw new Error(`Refusing to build a CSP: ${parsed.reason}`);
    connect = parsed.origin;
  }
  return [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    `connect-src ${connect}`,
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
  ].join("; ");
}
