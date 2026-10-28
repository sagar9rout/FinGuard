import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import { buildCsp } from "./src/lib/csp.ts";
import { resolveRuntime } from "./src/lib/runtime.ts";

// Production builds carry a Content-Security-Policy that forbids inline styles/scripts and, for network access, allows
// exactly one origin: none in mock mode, or the single validated loopback API origin in live mode. The same variables
// (VITE_FINGUARD_MODE, VITE_API_BASE_URL) drive the app's runtime mode, so policy and behaviour cannot diverge.
// An unusable configuration fails the build rather than widening the policy.
// (Not applied by the dev server: Vite's dev server needs inline scripts and a websocket for hot reload.)
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const runtime = resolveRuntime({ mode: env["VITE_FINGUARD_MODE"], apiBaseUrl: env["VITE_API_BASE_URL"] });
  if (runtime.mode === "misconfigured") throw new Error(`FinGuard client configuration error: ${runtime.reason}`);
  const csp = buildCsp(runtime.mode === "live" ? runtime.apiOrigin : null);

  return {
    plugins: [
      react(),
      {
        name: "finguard-csp",
        apply: "build",
        transformIndexHtml(html: string) {
          return html.replace("<head>", `<head>\n    <meta http-equiv="Content-Security-Policy" content="${csp}" />`);
        },
      },
    ],
    // No dev proxy: the browser calls the local API directly, which is why the server's CORS allow-list names this origin.
    server: { host: "localhost" },
  };
});
