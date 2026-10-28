# FinGuard client (Phase 1 prototype)

A React + TypeScript + Vite front end for FinGuard. **Everything on screen is sample data from a mock engine.**
A persistent banner says so. The interface never decides affordability: it displays committed engine-shaped sample
responses, and the assistant is a rule-based form helper, not an AI model.

## Run

Requires Node 22.18 or newer (the tests run TypeScript directly under Node).

```bash
cd client
npm install        # first time; creates package-lock.json
npm run dev        # http://localhost:5173
npm run build      # type-checks, then builds to dist/ (the build carries a no-network CSP)
npm run lint       # integrity guard (no network/storage/logging/float money) + ESLint
npm run typecheck  # tsc on the whole project
npm run test       # node --test on tests/**/*.test.ts
```

## Structure

```
client/
├── public/images/          static images (none yet)
├── src/
│   ├── assets/             bundled assets (none yet)
│   ├── components/
│   │   ├── layout/         AppShell, SampleBanner (always visible)
│   │   ├── dashboard/      Dashboard (summary, baseline outlook)
│   │   ├── horizon/        HorizonChart (baseline series + reserve only)
│   │   ├── decision/       DecisionCard, ReasonList, result/empty/error states
│   │   ├── assistant/      AssistantPanel (rule-based input helper)
│   │   └── forms/          BuyOrWaitForm
│   ├── pages/              OverviewPage, AnalysePage
│   ├── adapters/           AnalysisAdapter interface + MockAdapter (the only engine here)
│   ├── fixtures/           synthetic requests/responses captured from the in-process API handlers (engine 1.0.0-pr1.1)
│   ├── hooks/              useDashboard, useAnalysis (in-memory state, no persistence)
│   ├── lib/                pure logic: money text, Decision Card view-model, reason copy, form rules, assistant, chart geometry
│   ├── types/api.ts        wire types for the documented /v1 contract
│   ├── styles/             tokens.css, app.css
│   ├── App.tsx, main.tsx
├── tests/                  node --test suites (lib, adapters, fixtures)
├── scripts/check-integrity.mjs
└── .env.example            documents that Phase 1 reads no environment variables
```

The mock adapter returns committed samples chosen by the "Mock engine scenario" control; the result does not depend on
the entered amounts. The assistant is a rule-based form helper, not an AI model. `check-integrity.mjs` enforces the
no-network, no-storage, no-logging and no-float-money rules.

## Not in Phase 1

No backend calls, authentication, persistence, LLM, CORS or deployment. Reason-code copy comes from the draft
`docs/engine/reason-codes.md`; codes it does not document show a neutral fallback.

## Live mode (local engine, loopback only)

The app has two explicit modes, chosen by `VITE_FINGUARD_MODE` (`mock` is the default). The banner always says which one
is active: "SAMPLE DATA · MOCK ENGINE", "LOCAL ENGINE · PROTOTYPE", or "NOT CONNECTED · CONFIGURATION ERROR" (invalid
settings select no adapter and make no request). There is no sign-in, TLS or rate limiting; do not expose the server.

```bash
# terminal 1: the API (loopback only)
cd server && FINGUARD_CORS_ORIGINS=http://localhost:5173 python -m app.run      # http://127.0.0.1:8000
# terminal 2: the client
cd client && cp .env.example .env.local   # set VITE_FINGUARD_MODE=live and VITE_API_BASE_URL=http://127.0.0.1:8000
npm install && npm run dev                # http://localhost:5173
```

`VITE_API_BASE_URL` must be `http://localhost|127.0.0.1|[::1]:<port>` with no path; anything else fails the build.
`npm run build` injects a CSP whose `connect-src` is `'none'` (mock) or that single origin (live); the dev server sets no CSP.
The Overview sends the committed synthetic profile to `POST /v1/forecast`; the form sends `POST /v1/analyze`. The
adapter also implements `/health`, `/v1/meta`, `/v1/schema/analysis-request` and `/v1/validate`. Results are shown as
received (`outcome.certified` first); the client computes nothing.
