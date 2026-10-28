/**
 * Geometry for the Financial Horizon chart. PRESENTATION ONLY.
 *
 * Amounts are canonical decimal strings. To place them on a canvas without ever turning an amount into a
 * floating-point number, values are parsed into exact BigInt integers (scaled by a common power of ten) and the
 * pixel position is computed with integer arithmetic; only the finished pixel coordinate (a small integer in
 * hundredths of a pixel) is converted with Number(). Nothing here is shown as a financial figure: axis labels are
 * the engine's own strings, re-formatted. No forecast, extrapolation or smoothing is performed.
 */
import { formatDate, formatMoney, isCanonicalDecimal } from "./money.ts";
import type { LedgerDay } from "../types/api.ts";

export interface PlotDimensions {
  readonly width: number;
  readonly height: number;
  readonly left: number;
  readonly right: number;
  readonly top: number;
  readonly bottom: number;
}

export interface PlotModel {
  readonly closePath: string;
  readonly lowPath: string;
  readonly reserveY: string;
  readonly plotLeft: number;
  readonly plotRight: number;
  readonly maxLabel: string;
  readonly minLabel: string;
  readonly xLabels: readonly { readonly x: string; readonly text: string }[];
}

function scaledParts(value: string): { negative: boolean; digits: string; scale: number } {
  const negative = value.startsWith("-");
  const unsigned = negative ? value.slice(1) : value;
  const dot = unsigned.indexOf(".");
  const frac = dot === -1 ? "" : unsigned.slice(dot + 1);
  return { negative, digits: dot === -1 ? unsigned : unsigned.slice(0, dot) + frac, scale: frac.length };
}

function toScaled(value: string, scale: number): bigint {
  const p = scaledParts(value);
  const magnitude = BigInt(p.digits) * 10n ** BigInt(scale - p.scale);
  return p.negative ? -magnitude : magnitude;
}

function px(hundredths: bigint): string {
  const n = Number(hundredths); // pixel coordinate only
  return `${Math.trunc(n / 100)}.${String(Math.abs(n % 100)).padStart(2, "0")}`;
}

/** Returns null when the series is empty or contains any value that is not a canonical decimal string. */
export function buildHorizon(
  series: readonly LedgerDay[],
  reserve: string,
  currency: string,
  d: PlotDimensions,
): PlotModel | null {
  if (series.length === 0 || !isCanonicalDecimal(reserve)) return null;
  const all: string[] = [reserve];
  for (const day of series) all.push(day.low, day.close);
  if (!all.every(isCanonicalDecimal)) return null;

  const scale = Math.max(...all.map((v) => scaledParts(v).scale));
  const scaled = all.map((v) => toScaled(v, scale));
  let minIndex = 0;
  let maxIndex = 0;
  scaled.forEach((v, i) => {
    if (v < (scaled[minIndex] as bigint)) minIndex = i;
    if (v > (scaled[maxIndex] as bigint)) maxIndex = i;
  });
  const min = scaled[minIndex] as bigint;
  const max = scaled[maxIndex] as bigint;
  const span = max === min ? 1n : max - min;

  const innerW = BigInt((d.width - d.left - d.right) * 100);
  const innerH = BigInt((d.height - d.top - d.bottom) * 100);
  const top = BigInt(d.top * 100);
  const left = BigInt(d.left * 100);
  const y = (v: bigint): bigint => top + ((max - v) * innerH) / span;
  const lastIndex = BigInt(Math.max(series.length - 1, 1));
  const x = (i: number): bigint => left + (BigInt(i) * innerW) / lastIndex;

  const path = (offset: 1 | 2): string =>
    series.map((_, i) => `${i === 0 ? "M" : "L"}${px(x(i))} ${px(y(scaled[2 * i + offset] as bigint))}`).join(" ");

  const labelAt = (i: number): { x: string; text: string } => ({
    x: px(x(i)),
    text: formatDate((series[i] as LedgerDay).day),
  });
  const mid = Math.floor((series.length - 1) / 2);
  const idx = [...new Set([0, mid, series.length - 1])];

  return {
    closePath: path(2),
    lowPath: path(1),
    reserveY: px(y(scaled[0] as bigint)),
    plotLeft: d.left,
    plotRight: d.width - d.right,
    maxLabel: formatMoney(all[maxIndex] as string, currency),
    minLabel: formatMoney(all[minIndex] as string, currency),
    xLabels: idx.map(labelAt),
  };
}
