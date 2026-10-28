# FinGuard server (loopback-only HTTP layer)

A small Starlette application that exposes the **already implemented and tested** FinGuard API
(`backend/finguard_api`, ADR 0011, `docs/api/v1.md`) to the browser client. It contains **no financial logic**:
requests are forwarded as raw bytes to the backend handlers, which validate them and call the deterministic engine
(`backend/finguard_core`); responses are returned unchanged. If the engine cannot be loaded, engine routes answer
`503 {"error":{"code":"engine_unavailable"}}` — the server never fabricates or mocks a result.

## Routes (exactly the documented ones)

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | liveness only: `{"status":"ok"}` |
| GET | `/v1/meta` | engine version, statuses, reason codes, limits |
| GET | `/v1/schema/analysis-request` | JSON Schema of the request |
| POST | `/v1/validate` | always 200 with `valid` / `violations` |
| POST | `/v1/forecast` | baseline forecast, no decision |
| POST | `/v1/analyze` | the affordability analysis; branch on `outcome.certified` first |

Money is a decimal string or integer, never a float. Errors: `{"error":{"code","violations"?}}`.
This layer adds one code, `engine_unavailable` (503), and `invalid_host` (400) for non-loopback `Host` headers.

## Setup and run (Python 3.11+)

```bash
cd server
python -m venv .venv                      # keep the venv out of version control (.gitignore covers .venv/)
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt       # requires access to a package index
python -m pytest                          # run the tests
FINGUARD_CORS_ORIGINS=http://localhost:5173 python -m app.run   # http://127.0.0.1:8000
```

The server imports `finguard_api` and `finguard_core` from `../backend` (override with `FINGUARD_BACKEND_PATH`).
`python -m app.run` disables uvicorn's access log, which would record paths and query strings.

## Configuration (environment variables; see `.env.example`)

`FINGUARD_SERVER_HOST` (loopback only; `0.0.0.0` is refused), `FINGUARD_SERVER_PORT`, `FINGUARD_CORS_ORIGINS`,
`FINGUARD_MAX_BODY_BYTES`, `FINGUARD_LOG_LEVEL`, `FINGUARD_BACKEND_PATH`. There is no database or secret setting.

## Security posture (what is and is not implemented)

Implemented and tested: loopback-only bind, loopback-only `Host` header check (DNS-rebinding defence), CORS disabled
unless exact loopback origins are configured (the Vite dev origin is `http://localhost:5173`; no wildcard,
no credentials, only GET/POST and `Content-Type`), request size limit, strict request validation, errors without
request echo or stack traces, `no-store` responses, and logs limited to method, matched path, status, duration and a
server-generated request id.

**Not implemented:** authentication, authorization, tenant isolation, rate limiting, TLS, persistence, production
hardening. Do not expose this server beyond the local machine (ADR 0011). The browser never talks to PostgreSQL.

## Client note

`client/vite.config.ts` currently ships a production CSP with `connect-src 'none'` and the client has no live adapter.
Integration needs a separate, approved client change; this layer does not modify `client/`.
