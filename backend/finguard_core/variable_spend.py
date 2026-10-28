"""Essential variable spending estimate (docs/engine/semantics.md
Section 5, step 5): method ``weekly_p75_nearest_rank_v1`` (ADR 0010).

Definition (locked):
- History is measured from the earliest settled event dated before
  ``as_of`` to ``as_of``. Under ``variable_spend_min_history_days`` (14)
  there is NO estimate.
- Only complete 7-day blocks counted backward from ``as_of`` are used:
  ``complete_weeks = min(history_days, lookback_days) // 7``.
- A block with no spending is a zero week and COUNTS; ``weeks_used``
  (``complete_weeks_used``) includes zero weeks.
- Fewer than ``variable_spend_min_weeks_for_percentile`` (4) complete
  weeks: the estimate is the MAXIMUM weekly total. Otherwise the
  nearest-rank 75th percentile of all weekly totals.
- ``daily = weekly_value / 7``, rounded up to the home minor unit.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_CEILING, Decimal

from finguard_core.contracts import (
    EngineConfig,
    EventDirection,
    EventStatus,
    FinancialEventInput,
    FxRateEntry,
    VariableSpendInfo,
)
from finguard_core.currency import Currency, RoundingDirection, round_money
from finguard_core.fx import FxUsageLog, convert_amount
from finguard_core.reason_codes import ReasonCode

METHOD = "weekly_p75_nearest_rank_v1"


@dataclass(frozen=True, slots=True)
class VariableSpendEstimate:
    info: VariableSpendInfo
    reason_codes: tuple[ReasonCode, ...]
    blocked: bool

    @property
    def daily_amount(self) -> Decimal | None:
        return self.info.daily_amount

    @property
    def categories(self) -> tuple[str, ...]:
        return self.info.categories


def _nearest_rank_percentile(values: Sequence[Decimal], percentile: Decimal) -> Decimal:
    ordered = sorted(values)
    n = len(ordered)
    rank = (percentile * n / Decimal(100)).to_integral_value(rounding=ROUND_CEILING)
    rank = max(Decimal(1), min(Decimal(n), rank))
    return ordered[int(rank) - 1]


def _empty_info(
    categories: tuple[str, ...], config: EngineConfig, history_days: int, weeks: int
) -> VariableSpendInfo:
    return VariableSpendInfo(
        method=METHOD,
        estimated=False,
        categories=categories,
        lookback_days=config.variable_spend_lookback_days,
        history_days=history_days,
        complete_weeks_used=weeks,
        zero_weeks=0,
        weekly_totals=(),
        statistic="none",
        weekly_value=None,
        daily_amount=None,
        currency=None,
    )


def estimate_variable_spend(
    events: Sequence[FinancialEventInput],
    categories: Sequence[str],
    as_of: date,
    home_currency: str,
    home_registry_currency: Currency,
    config: EngineConfig,
    fx_rates: Sequence[FxRateEntry] = (),
    usage: FxUsageLog | None = None,
) -> VariableSpendEstimate:
    cats = tuple(sorted(set(categories)))
    settled_dates = [e.event_date for e in events if e.status is EventStatus.SETTLED and e.event_date < as_of]
    history_days = (as_of - min(settled_dates)).days if settled_dates else 0

    if not cats:
        return VariableSpendEstimate(_empty_info(cats, config, history_days, 0), (), False)

    if history_days < config.variable_spend_min_history_days:
        return VariableSpendEstimate(
            _empty_info(cats, config, history_days, 0),
            (ReasonCode.VARIABLE_SPEND_INSUFFICIENT_HISTORY, ReasonCode.INSUFFICIENT_HISTORY),
            False,
        )

    window_days = min(history_days, config.variable_spend_lookback_days)
    weeks = window_days // 7
    totals = [Decimal(0)] * weeks
    blocked = False
    for event in events:
        if (
            event.category not in cats
            or event.direction is not EventDirection.DEBIT
            or event.status is not EventStatus.SETTLED
            or event.amount is None
            or not (as_of - timedelta(days=7 * weeks) <= event.event_date < as_of)
        ):
            continue
        converted, _codes, blocks = convert_amount(
            event.amount,
            event.currency,
            home_currency,
            event.event_date,
            fx_rates,
            config,
            True,
            home_registry_currency,
            usage,
        )
        if blocks or converted is None:
            blocked = True
            continue
        block_index = (as_of - event.event_date - timedelta(days=1)).days // 7
        totals[block_index] += converted

    if blocked:
        return VariableSpendEstimate(
            _empty_info(cats, config, history_days, weeks), (ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION,), True
        )

    if weeks < config.variable_spend_min_weeks_for_percentile:
        weekly_value = max(totals)
        statistic = "max_weekly_total"
    else:
        weekly_value = _nearest_rank_percentile(totals, Decimal(75))
        statistic = "p75_nearest_rank"

    daily = round_money(weekly_value / Decimal(7), home_registry_currency, RoundingDirection.UP)
    info = VariableSpendInfo(
        method=METHOD,
        estimated=True,
        categories=cats,
        lookback_days=config.variable_spend_lookback_days,
        history_days=history_days,
        complete_weeks_used=weeks,
        zero_weeks=sum(1 for t in totals if t == 0),
        weekly_totals=tuple(totals),
        statistic=statistic,
        weekly_value=weekly_value,
        daily_amount=daily,
        currency=home_currency,
    )
    return VariableSpendEstimate(info, (ReasonCode.VARIABLE_SPEND_ESTIMATED,), False)
