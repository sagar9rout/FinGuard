#!/usr/bin/env node
/**
 * Repository-local guard for the properties this prototype promises (run first by `npm run lint`).
 *
 *  - no storage, logging or cookie APIs anywhere; network calls (`fetch(`) only in adapters/liveAdapter.ts;
 *  - `http:` URL text only in the origin validator (lib/apiOrigin.ts) and the tests that exercise it;
 *  - no floating-point number formatting or parsing of money (money stays a decimal string);
 *  - no inline `style` attributes (the production CSP forbids them) and no external URLs;
 *  - the sample-data banner exists and is mounted by the app shell;
 *  - the live adapter is the only network code, never sends credentials, and the CSP builder has no wildcard or
 *    'unsafe-*' source; vite.config.ts must build its CSP with buildCsp.
 *
 * Comments are stripped before scanning so documentation can describe what is forbidden. Test files are scanned
 * only for the network/storage/logging rules.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(root, "src");
const tests = join(root, "tests");

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else out.push(p);
  }
  return out;
}

function stripComments(text) {
  return text.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`\\])\/\/.*$/gm, "$1");
}

const NETWORK_AND_STORAGE = [
  [/\bfetch\s*\(/, "fetch() call"],
  [/\bXMLHttpRequest\b/, "XMLHttpRequest"],
  [/\bWebSocket\b/, "WebSocket"],
  [/\bEventSource\b/, "EventSource"],
  [/\bsendBeacon\b/, "sendBeacon"],
  [/\blocalStorage\b/, "localStorage"],
  [/\bsessionStorage\b/, "sessionStorage"],
  [/\bindexedDB\b/, "indexedDB"],
  [/\bdocument\.cookie\b/, "document.cookie"],
  [/\bconsole\s*\./, "console output"],
  [/\bimport\s*\(/, "dynamic import"],
  [/https?:/, "external URL"],
];
const PRESENTATION_ONLY = [
  [/\bparseFloat\b/, "parseFloat"],
  [/\bparseInt\b/, "parseInt"],
  [/\.toFixed\s*\(/, "toFixed"],
  [/\bIntl\.NumberFormat\b/, "Intl.NumberFormat"],
  [/\.toLocaleString\s*\(/, "toLocaleString"],
  [/\bNumber\s*\(/, "Number() conversion"],
  [/\bstyle\s*=\s*\{/, "inline style attribute"],
];
// Files that may use Number(): the chart geometry converts finished pixel coordinates; the form converts a
// validated whole number of days. Neither touches an amount.
const NUMBER_ALLOWED = new Set(["lib/plot.ts", "lib/form.ts"]);

// Narrow, explicit allowances. Everything else stays forbidden.
const FETCH_ALLOWED = new Set(["adapters/liveAdapter.ts"]);
const URL_TEXT_ALLOWED = new Set([
  "lib/apiOrigin.ts",
  "tests/lib/apiOrigin.test.ts",
  "tests/lib/csp.test.ts",
  "tests/lib/runtime.test.ts",
  "tests/adapters/liveAdapter.test.ts",
  "tests/adapters/selectAdapter.test.ts",
]);

const problems = [];
const files = [...walk(src), ...walk(tests)];
for (const file of files) {
  const rel = relative(root, file).replaceAll("\\", "/").replace(/^src\//, "");
  if (!/\.(ts|tsx)$/.test(rel)) continue;
  const isTest = /\.test\.ts$/.test(rel);
  const text = stripComments(readFileSync(file, "utf8"));
  for (const [re, label] of NETWORK_AND_STORAGE) {
    if (label === "fetch() call" && FETCH_ALLOWED.has(rel)) continue;
    if (label === "external URL" && URL_TEXT_ALLOWED.has(rel)) continue;
    if (re.test(text)) problems.push(`${rel}: forbidden ${label}`);
  }
  if (isTest) continue;
  for (const [re, label] of PRESENTATION_ONLY) {
    if (label === "Number() conversion" && NUMBER_ALLOWED.has(rel)) continue;
    if (re.test(text)) problems.push(`${rel}: forbidden ${label}`);
  }
  if (/\bkind\s*=\s*"live"|kind:\s*"live"\s*[,}]/.test(text) && rel.startsWith("adapters/") && !FETCH_ALLOWED.has(rel) && !rel.endsWith("analysisAdapter.ts"))
    problems.push(`${rel}: only adapters/liveAdapter.ts may implement the live adapter`);
}

const live = readFileSync(join(src, "adapters", "liveAdapter.ts"), "utf8");
if (!/credentials:\s*"omit"/.test(live)) problems.push('adapters/liveAdapter.ts must send requests with credentials: "omit"');
const cspSrc = stripComments(readFileSync(join(src, "lib", "csp.ts"), "utf8"));
if (/unsafe-|\*/.test(cspSrc)) problems.push("lib/csp.ts must not contain a wildcard or 'unsafe-*' source");
if (!/buildCsp\(/.test(readFileSync(join(root, "vite.config.ts"), "utf8"))) problems.push("vite.config.ts must build its CSP with buildCsp()");

const css = files.filter((f) => f.endsWith(".css"));
for (const file of css) {
  const text = readFileSync(file, "utf8");
  if (/@import|url\(\s*["']?https?:/i.test(text)) problems.push(`${relative(root, file)}: external CSS resource`);
}

const bannerFile = join(src, "components", "layout", "SampleBanner.tsx");
let banner = "";
try {
  banner = readFileSync(bannerFile, "utf8");
} catch {
  problems.push("components/layout/SampleBanner.tsx is missing");
}
if (!banner.includes("SAMPLE DATA · MOCK ENGINE")) problems.push('SampleBanner must contain "SAMPLE DATA · MOCK ENGINE"');
const shell = readFileSync(join(src, "components", "layout", "AppShell.tsx"), "utf8");
if (!/<SampleBanner\b/.test(shell)) problems.push("AppShell.tsx must mount <SampleBanner />");
if (!/<AppShell\b/.test(readFileSync(join(src, "App.tsx"), "utf8"))) problems.push("App.tsx must render <AppShell>");

if (problems.length > 0) {
  process.stderr.write(`integrity check FAILED (${problems.length})\n${problems.map((p) => `  - ${p}`).join("\n")}\n`);
  process.exit(1);
}
process.stdout.write(`integrity check passed (${files.length} files scanned)\n`);
