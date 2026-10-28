/**
 * Validation of the one API origin the client may talk to.
 *
 * The server layer is loopback-only and speaks plain HTTP (no TLS, ADR 0011), so the only acceptable origin is
 * `http://localhost:<port>`, `http://127.0.0.1:<port>` or `http://[::1]:<port>`. An explicit port is required. No
 * wildcard, no path, query, fragment or credentials, no other host and no other scheme is accepted. The same function
 * decides the runtime origin and the Content-Security-Policy `connect-src`, so the two cannot disagree.
 */
export type OriginResult = { readonly ok: true; readonly origin: string } | { readonly ok: false; readonly reason: string };

const PATTERN = /^http:\/\/(localhost|127\.0\.0\.1|\[::1\]):([1-9][0-9]{0,4})\/?$/;

export function parseApiOrigin(raw: string | undefined): OriginResult {
  const text = (raw ?? "").trim();
  if (text === "") return { ok: false, reason: "No API origin is configured." };
  const m = PATTERN.exec(text);
  if (m === null) {
    return {
      ok: false,
      reason: "The API origin must look like http://127.0.0.1:8000 (a loopback host and an explicit port; no path, wildcard or other host).",
    };
  }
  const host = m[1] ?? "";
  const port = m[2] ?? "";
  // Port range without numeric conversion: equal-length digit strings compare correctly.
  if (port.length === 5 && port > "65535") return { ok: false, reason: "The API origin port is out of range." };
  return { ok: true, origin: `http://${host}:${port}` };
}
