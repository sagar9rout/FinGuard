import { useEffect, useRef, useState } from "react";
import { formatDate, formatMoney } from "../../lib/money.ts";
import { buildHorizon } from "../../lib/plot.ts";
import type { LedgerDay } from "../../types/api.ts";

interface Props {
  readonly series: readonly LedgerDay[];
  readonly reserve: string;
  readonly currency: string;
}

const MARGIN = { left: 12, right: 12, top: 24, bottom: 46 } as const;

/**
 * Financial Horizon: the engine's documented BASELINE series (closing balance and lowest point of each day, no
 * purchase) against the reserve threshold. There is no post-purchase series in the documented contract, so none is
 * drawn. Positions come from plot.ts; this component adds no numbers of its own.
 */
export function HorizonChart({ series, reserve, currency }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);

  useEffect(() => {
    const el = box.current;
    if (el === null || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w !== undefined && w >= 240) setWidth(Math.min(Math.floor(w), 960));
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const height = width < 480 ? 240 : 300;
  const model = buildHorizon(series, reserve, currency, { width, height, ...MARGIN });
  if (model === null) {
    return <p className="state-note">The forecast series could not be drawn from the data provided.</p>;
  }
  const first = series[0] as LedgerDay;
  const last = series[series.length - 1] as LedgerDay;
  const reserveText = formatMoney(reserve, currency);
  const label =
    `Financial Horizon, baseline without the purchase, ${formatDate(first.day)} to ${formatDate(last.day)}. ` +
    `Highest plotted value ${model.maxLabel}, lowest ${model.minLabel}, reserve ${reserveText}.`;

  return (
    <figure className="horizon">
      <div ref={box} className="horizon__plot">
        <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="img" aria-label={label}>
          <line className="horizon__axis" x1={model.plotLeft} x2={model.plotRight} y1={MARGIN.top} y2={MARGIN.top} />
          <line
            className="horizon__axis"
            x1={model.plotLeft}
            x2={model.plotRight}
            y1={height - MARGIN.bottom}
            y2={height - MARGIN.bottom}
          />
          <text className="horizon__label" x={model.plotLeft} y={MARGIN.top - 8}>
            {model.maxLabel}
          </text>
          <text className="horizon__label" x={model.plotLeft} y={height - MARGIN.bottom + 16}>
            {model.minLabel}
          </text>
          <path className="horizon__low" d={model.lowPath} fill="none" />
          <path className="horizon__close" d={model.closePath} fill="none" />
          <line
            className="horizon__reserve"
            x1={model.plotLeft}
            x2={model.plotRight}
            y1={model.reserveY}
            y2={model.reserveY}
          />
          <text className="horizon__label horizon__label--reserve" x={model.plotRight} y={model.reserveY} dy={-6} textAnchor="end">
            {`Reserve ${reserveText}`}
          </text>
          {model.xLabels.map((l, i) => (
            <text
              key={`${l.x}-${l.text}`}
              className="horizon__label"
              x={l.x}
              y={height - 6}
              textAnchor={i === 0 ? "start" : i === model.xLabels.length - 1 ? "end" : "middle"}
            >
              {l.text}
            </text>
          ))}
        </svg>
      </div>
      <figcaption className="horizon__legend">
        <span className="key key--close">Closing balance</span>
        <span className="key key--low">Lowest point of the day</span>
        <span className="key key--reserve">Reserve (minimum to keep)</span>
      </figcaption>
      <details className="horizon__table">
        <summary>View the plotted values as a table</summary>
        <div className="table-scroll">
          <table>
            <caption className="sr-only">Baseline balance by day</caption>
            <thead>
              <tr>
                <th scope="col">Day</th>
                <th scope="col" className="num">Lowest point</th>
                <th scope="col" className="num">Closing balance</th>
              </tr>
            </thead>
            <tbody>
              {series.map((d) => (
                <tr key={d.day}>
                  <th scope="row">{formatDate(d.day)}</th>
                  <td className="num">{formatMoney(d.low, currency)}</td>
                  <td className="num">{formatMoney(d.close, currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
