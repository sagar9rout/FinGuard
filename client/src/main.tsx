import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App.tsx";
import { resolveRuntime } from "./lib/runtime.ts";
import "./styles/tokens.css";
import "./styles/app.css";

interface FinGuardEnv {
  readonly VITE_FINGUARD_MODE?: string;
  readonly VITE_API_BASE_URL?: string;
}
// Vite replaces import.meta.env at build time. The same variables drive the CSP in vite.config.ts.
const env = (import.meta as unknown as { readonly env: FinGuardEnv }).env;
const runtime = resolveRuntime({ mode: env.VITE_FINGUARD_MODE, apiBaseUrl: env.VITE_API_BASE_URL });

const container = document.getElementById("root");
if (container === null) throw new Error("Missing #root element");
createRoot(container).render(
  <StrictMode>
    <App runtime={runtime} />
  </StrictMode>,
);
