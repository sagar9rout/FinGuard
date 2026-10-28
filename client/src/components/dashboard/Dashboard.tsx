import type { AdapterError, DashboardProfile } from "../../adapters/analysisAdapter.ts";
import { DASHBOARD_STATES, type DashboardStateKey } from "../../adapters/mockAdapter.ts";
import { describeReasons } from "../../lib/reasons.ts";
import { formatDate, formatMoney } from "../../lib/money.ts";
import type { ForecastResponse } from "../../types/api.ts";
import { HorizonChart } from "../horizon/HorizonChart.tsx";
import { ReasonList } from "../decision/ReasonList.tsx";

export type DashboardState =
  | { readonly kind: "loading" }
  | { readonly kind: "error"; readonly error: AdapterError }
  | { readonly kind: "ready"; readonly profile: DashboardProfile; readonly forecast: ForecastResponse };

interface Props {
  readonly state: DashboardState;
  readonly mode: "mock" | "live";
  readonly mockState: DashboardStateKey;
  readonly onMockState: (key: DashboardStateKey) => void;
  readonly onRetry: () => void;
  readonly onAnalyse: () => void;
}

export function Dashboard({ state, mode, mockState, onMockState, onRetry, onAnalyse }: Props) {
  return (
    <div className="page">
      <div className="page__head">
        <div>
          <h1>Overview</h1>
          <p className="lede">A synthetic profile and the engine&apos;s baseline outlook with no purchase.</p>
        </div>
        <button type="button" className="btn btn--primary" onClick={onAnalyse}>
          Buy or wait?
        </button>
      </div>

      {mode === "mock" && (
      <div className="mock-control">
        <label htmlFor="mock-dashboard">Mock data state</label>
        <select id="mock-dashboard" value={mockState} onChange={(e) => onMockState(e.target.value as DashboardStateKey)}>
          {DASHBOARD_STATES.map((s) => (
            <option key={s.key} value={s.key}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
      )}

      {state.kind === "loading" && (
        <div className="skeleton" role="status" aria-live="polite" aria-busy="true">
          <span className="sr-only">Loading the forecast…</span>
          <div className="skeleton__row" />
          <div className="skeleton__row skeleton__row--tall" />
        </div>
      )}

      {state.kind === "error" && (
        <div className="notice notice--error" role="alert">
          <h2>The forecast could not be loaded</h2>
          <p>
            {mode === "mock" ? "The mock engine" : "The local engine"} returned an error (<code>{state.error.code}</code>, status {state.error.status}). Nothing has been
            assumed in its place.
          </p>
          <button type="button" className="btn" onClick={onRetry}>
            Try again
          </button>
        </div>
      )}

      {state.kind === "ready" && <Ready profile={state.profile} forecast={state.forecast} mode={mode} />}
    </div>
  );
}

function Ready({ profile, forecast, mode }: { profile: DashboardProfile; forecast: ForecastResponse; mode: "mock" | "live" }) {
  const cur = profile.homeCurrency;
  const result = forecast.result;
  const base = result.baseline_summary;
  const w = result.certifiable_window;
  const empty = result.baseline_series.length === 0;
  return (
    <>
      {mode === "live" && (
        <p className="muted small">
          Demo profile: its figures and dates are invented and fixed for reproducibility, so they are not today&apos;s date.
        </p>
      )}
      <section aria-labelledby="summary-h" className="summary">
        <h2 id="summary-h" className="sr-only">
          Balance and reserve
        </h2>
        <div className="figure">
          <span className="figure__label">Available balance</span>
          <span className="figure__value num">{formatMoney(profile.balance, cur)}</span>
          <span className="figure__note">
            {profile.balanceAsOf === null ? "Balance date not given" : `As of ${formatDate(profile.balanceAsOf)}`}
          </span>
        </div>
        <div className="figure">
          <span className="figure__label">Reserve to keep</span>
          <span className="figure__value num">{formatMoney(profile.reserve, cur)}</span>
          <span className="figure__note">Your minimum balance, as entered</span>
        </div>
        <div className="figure">
          <span className="figure__label">Baseline lowest point</span>
          <span className="figure__value num">{base.lowest === null ? "—" : formatMoney(base.lowest.balance, cur)}</span>
          <span className="figure__note">{base.lowest === null ? "No lowest point reported" : `On ${formatDate(base.lowest.day)}`}</span>
        </div>
      </section>

      <section aria-labelledby="horizon-h" className="panel">
        <div className="panel__head">
          <h2 id="horizon-h">Financial Horizon</h2>
          <p className="muted">
            Baseline balance without the purchase, {formatDate(w.start)} to {formatDate(w.effective_end)}
            {w.truncated ? " (window truncated by the engine)" : ""}.
          </p>
        </div>
        {empty ? (
          <div className="empty">
            <h3>No forecast data</h3>
            <p>The engine returned no baseline series, so there is nothing to draw. The reserve is not plotted on its own.</p>
          </div>
        ) : (
          <HorizonChart series={result.baseline_series} reserve={profile.reserve} currency={cur} />
        )}
      </section>

      <section aria-labelledby="outlook-h" className="panel">
        <h2 id="outlook-h">Baseline outlook (engine output)</h2>
        <dl className="facts">
          <div>
            <dt>Baseline below reserve</dt>
            <dd>{base.below_reserve ? "Yes" : "No"}</dd>
          </div>
          <div>
            <dt>Days below reserve</dt>
            <dd className="num">{base.days_below}</dd>
          </div>
          <div>
            <dt>Largest shortfall</dt>
            <dd className="num">{formatMoney(base.max_shortfall, cur)}</dd>
          </div>
          {base.first_breach_date !== null && (
            <div>
              <dt>First day below</dt>
              <dd>{formatDate(base.first_breach_date)}</dd>
            </div>
          )}
          {base.last_breach_date !== null && (
            <div>
              <dt>Last day below</dt>
              <dd>{formatDate(base.last_breach_date)}</dd>
            </div>
          )}
        </dl>
        <p className="muted small">
          This describes the baseline only. It is not a purchase decision; the engine reports decisions through the Buy or Wait
          analysis.
        </p>
        {(result.assumptions.length > 0 || result.issues.length > 0) && (
          <details className="disclosure">
            <summary>Forecast assumptions and data issues</summary>
            <ReasonList title="Assumptions" items={describeReasons(result.assumptions, cur)} empty="None reported." />
            <ReasonList title="Data issues" items={describeReasons(result.issues, cur)} empty="None reported." />
          </details>
        )}
        <p className="muted small">
          {mode === "mock" ? "Engine version of these samples" : "Engine version"}: <code>{forecast.engine_version}</code>
        </p>
      </section>
    </>
  );
}
