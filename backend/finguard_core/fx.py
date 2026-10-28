"""Foreign-exchange resolution (docs/engine/semantics.md Section 7;
ADR 0003).

Resolution for a ``(base, quote, date)`` triple happens in stages, each
tried only if the previous fails. A rate is stored as "units of
``quote_currency`` per 1 unit of ``base_currency``"; converting an
amount denominated in ``base_currency`` multiplies by the rate.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum

from finguard_core.contracts import EngineConfig, FxRateEntry, FxUsageEntry
from finguard_core.currency import Currency, RoundingDirection, round_money
from finguard_core.reason_codes import ReasonCode


class FxStage(StrEnum):
    EXACT = "exact"
    PRIOR = "prior"
    TRIANGULATED = "triangulated"
    PESSIMISTIC_BOUND = "pessimistic_bound"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class FxResolution:
    rate: Decimal | None
    stage: FxStage
    used_inverse: bool
    rate_date: date | None
    age_days: int | None
    reason_codes: tuple[ReasonCode, ...]
    blocks_certification: bool
    candidates_considered: int = 0


def _direct_rate(
    fx_rates: Sequence[FxRateEntry], base: str, quote: str, on_date: date
) -> tuple[Decimal, date, bool] | None:
    for entry in fx_rates:
        if entry.base_currency == base and entry.quote_currency == quote and entry.rate_date == on_date:
            return entry.rate, entry.rate_date, False
    for entry in fx_rates:
        if entry.base_currency == quote and entry.quote_currency == base and entry.rate_date == on_date:
            return Decimal(1) / entry.rate, entry.rate_date, True
    return None


def _latest_prior_rate(
    fx_rates: Sequence[FxRateEntry],
    base: str,
    quote: str,
    on_date: date,
    window_days: int,
) -> tuple[Decimal, date, bool] | None:
    earliest = on_date - timedelta(days=window_days)
    candidates: list[tuple[date, Decimal, bool]] = []
    for entry in fx_rates:
        if entry.rate_date >= on_date or entry.rate_date < earliest:
            continue
        if entry.base_currency == base and entry.quote_currency == quote:
            candidates.append((entry.rate_date, entry.rate, False))
        elif entry.base_currency == quote and entry.quote_currency == base:
            candidates.append((entry.rate_date, Decimal(1) / entry.rate, True))
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c[0], canonical_tiebreak(c[1])))
    best_date = candidates[-1][0]
    same_date = [c for c in candidates if c[0] == best_date]
    same_date.sort(key=lambda c: canonical_tiebreak(c[1]))
    rate_date, rate, inverse = same_date[0]
    return rate, rate_date, inverse


def canonical_tiebreak(rate: Decimal) -> str:
    return format(rate.normalize(), "f")


def _resolve_direct_or_prior(
    fx_rates: Sequence[FxRateEntry],
    base: str,
    quote: str,
    on_date: date,
    config: EngineConfig,
) -> tuple[Decimal, FxStage, date, bool] | None:
    direct = _direct_rate(fx_rates, base, quote, on_date)
    if direct is not None:
        rate, rate_date, inverse = direct
        return rate, FxStage.EXACT, rate_date, inverse
    prior = _latest_prior_rate(fx_rates, base, quote, on_date, config.fx_prior_window_days)
    if prior is not None:
        rate, rate_date, inverse = prior
        return rate, FxStage.PRIOR, rate_date, inverse
    return None


def _triangulate(
    fx_rates: Sequence[FxRateEntry],
    base: str,
    quote: str,
    on_date: date,
    config: EngineConfig,
    is_debit: bool,
) -> tuple[Decimal, date] | None:
    results: list[tuple[Decimal, date]] = []
    for pivot in config.fx_pivot_currencies:
        if pivot == base or pivot == quote:
            continue
        leg1 = _resolve_direct_or_prior(fx_rates, base, pivot, on_date, config)
        leg2 = _resolve_direct_or_prior(fx_rates, pivot, quote, on_date, config)
        if leg1 is None or leg2 is None:
            continue
        rate = leg1[0] * leg2[0]
        leg_date = min(leg1[2], leg2[2])
        results.append((rate, leg_date))
    if not results:
        return None
    results.sort(key=lambda r: (r[0] if is_debit else -r[0], canonical_tiebreak(r[0])))
    # Least favorable: for a debit, the largest quote-per-base rate (costs
    # more); for a credit, the smallest (receives less).
    if is_debit:
        chosen = max(results, key=lambda r: r[0])
    else:
        chosen = min(results, key=lambda r: r[0])
    return chosen


def _pessimistic_bound(
    fx_rates: Sequence[FxRateEntry],
    base: str,
    quote: str,
    on_date: date,
    config: EngineConfig,
) -> tuple[Decimal, date, int] | None:
    earliest = on_date - timedelta(days=config.fx_pessimistic_window_days)
    candidates: list[tuple[Decimal, date]] = []
    for entry in fx_rates:
        if entry.rate_date > on_date or entry.rate_date < earliest:
            continue
        if entry.base_currency == base and entry.quote_currency == quote:
            candidates.append((entry.rate, entry.rate_date))
        elif entry.base_currency == quote and entry.quote_currency == base:
            candidates.append((Decimal(1) / entry.rate, entry.rate_date))
    for pivot in config.fx_pivot_currencies:
        if pivot == base or pivot == quote:
            continue
        leg1_candidates = [
            (e.rate, e.rate_date)
            for e in fx_rates
            if e.base_currency == base and e.quote_currency == pivot and earliest <= e.rate_date <= on_date
        ] + [
            (Decimal(1) / e.rate, e.rate_date)
            for e in fx_rates
            if e.base_currency == pivot and e.quote_currency == base and earliest <= e.rate_date <= on_date
        ]
        leg2_candidates = [
            (e.rate, e.rate_date)
            for e in fx_rates
            if e.base_currency == pivot and e.quote_currency == quote and earliest <= e.rate_date <= on_date
        ] + [
            (Decimal(1) / e.rate, e.rate_date)
            for e in fx_rates
            if e.base_currency == quote and e.quote_currency == pivot and earliest <= e.rate_date <= on_date
        ]
        for r1, d1 in leg1_candidates:
            for r2, d2 in leg2_candidates:
                candidates.append((r1 * r2, min(d1, d2)))
    if not candidates:
        return None
    # Least favorable for a debit is always the bound's purpose (this
    # stage is debit-only per Section 7).
    chosen = max(candidates, key=lambda c: (c[0], c[1].toordinal()))
    return chosen[0], chosen[1], len(candidates)


def resolve_fx(
    fx_rates: Sequence[FxRateEntry],
    base: str,
    quote: str,
    on_date: date,
    config: EngineConfig,
    is_debit: bool,
) -> FxResolution:
    """Resolve the conversion rate for one unit of ``base`` into
    ``quote`` on ``on_date``, per the staged policy. ``base`` is the
    event's own currency; ``quote`` is the home currency.
    """

    if base == quote:
        return FxResolution(
            rate=Decimal(1),
            stage=FxStage.EXACT,
            used_inverse=False,
            rate_date=on_date,
            age_days=0,
            reason_codes=(),
            blocks_certification=False,
        )

    direct = _direct_rate(fx_rates, base, quote, on_date)
    if direct is not None:
        rate, rate_date, inverse = direct
        exact_codes: tuple[ReasonCode, ...] = (ReasonCode.FX_INVERSE_USED,) if inverse else ()
        return FxResolution(rate, FxStage.EXACT, inverse, rate_date, 0, exact_codes, False)

    prior = _latest_prior_rate(fx_rates, base, quote, on_date, config.fx_prior_window_days)
    if prior is not None:
        rate, rate_date, inverse = prior
        prior_codes: tuple[ReasonCode, ...] = (ReasonCode.FX_PRIOR_RATE_USED,)
        if inverse:
            prior_codes = prior_codes + (ReasonCode.FX_INVERSE_USED,)
        return FxResolution(
            rate, FxStage.PRIOR, inverse, rate_date, (on_date - rate_date).days, prior_codes, False
        )

    triangulated = _triangulate(fx_rates, base, quote, on_date, config, is_debit)
    if triangulated is not None:
        rate, rate_date = triangulated
        return FxResolution(
            rate,
            FxStage.TRIANGULATED,
            False,
            rate_date,
            (on_date - rate_date).days,
            (ReasonCode.FX_TRIANGULATED,),
            False,
        )

    if is_debit:
        bound = _pessimistic_bound(fx_rates, base, quote, on_date, config)
        if bound is not None:
            rate, rate_date, considered = bound
            return FxResolution(
                rate,
                FxStage.PESSIMISTIC_BOUND,
                False,
                rate_date,
                (on_date - rate_date).days,
                (ReasonCode.FX_PESSIMISTIC_BOUND_USED,),
                False,
                considered,
            )
        return FxResolution(
            None,
            FxStage.UNRESOLVED,
            False,
            None,
            None,
            (ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION,),
            True,
        )

    return FxResolution(
        None,
        FxStage.UNRESOLVED,
        False,
        None,
        None,
        (ReasonCode.UNCONVERTIBLE_CREDIT_EXCLUDED,),
        False,
    )


@dataclass(slots=True)
class _UsageRow:
    count: int = 0
    worst_age: int | None = None
    worst_rate: Decimal | None = None
    inverse: int = 0
    considered: int = 0


class FxUsageLog:
    """Order-independent accumulator of every conversion's resolution
    stage, for the ``fx_usage`` result field. Every statistic is a
    commutative aggregate (count, max, min), so the final tuple is
    identical regardless of conversion order.
    """

    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._rows: dict[tuple[str, str, str, str], _UsageRow] = {}

    def record(self, base: str, quote: str, is_debit: bool, resolution: FxResolution) -> None:
        if base == quote:
            return
        direction = "debit" if is_debit else "credit"
        row = self._rows.setdefault((base, quote, resolution.stage.value, direction), _UsageRow())
        row.count += 1
        if resolution.age_days is not None:
            row.worst_age = resolution.age_days if row.worst_age is None else max(row.worst_age, resolution.age_days)
        if resolution.rate is not None:
            if row.worst_rate is None:
                row.worst_rate = resolution.rate
            else:
                row.worst_rate = (
                    max(row.worst_rate, resolution.rate) if is_debit else min(row.worst_rate, resolution.rate)
                )
        if resolution.used_inverse:
            row.inverse += 1
        row.considered = max(row.considered, resolution.candidates_considered)

    def entries(self) -> tuple[FxUsageEntry, ...]:
        out: list[FxUsageEntry] = []
        for key in sorted(self._rows):
            base, quote, stage, direction = key
            row = self._rows[key]
            is_pess = stage == FxStage.PESSIMISTIC_BOUND.value
            out.append(
                FxUsageEntry(
                    base_currency=base,
                    quote_currency=quote,
                    stage=stage,
                    direction=direction,
                    count=row.count,
                    worst_age_days=row.worst_age,
                    worst_rate=row.worst_rate,
                    inverse_used_count=row.inverse,
                    window_days=self._config.fx_pessimistic_window_days if is_pess else None,
                    candidates_considered=row.considered if is_pess else None,
                )
            )
        return tuple(out)


def convert_amount(
    amount: Decimal,
    currency: str,
    home_currency: str,
    on_date: date,
    fx_rates: Sequence[FxRateEntry],
    config: EngineConfig,
    is_debit: bool,
    home_registry_currency: Currency,
    usage: FxUsageLog | None = None,
) -> tuple[Decimal | None, tuple[ReasonCode, ...], bool]:
    """Convert ``amount`` into ``home_currency`` per the staged FX policy
    (ADR 0003), rounding at this documented boundary per ADR 0006
    (debits up, credits down). Returns ``(converted, reason_codes,
    blocks_certification)``; ``converted`` is None when unresolved.
    """

    resolution = resolve_fx(fx_rates, currency, home_currency, on_date, config, is_debit)
    if usage is not None:
        usage.record(currency, home_currency, is_debit, resolution)
    if resolution.rate is None:
        return None, resolution.reason_codes, resolution.blocks_certification
    converted = amount * resolution.rate
    direction = RoundingDirection.UP if is_debit else RoundingDirection.DOWN
    return round_money(converted, home_registry_currency, direction), resolution.reason_codes, False
