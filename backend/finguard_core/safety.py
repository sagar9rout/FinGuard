"""The G.9 safety predicate and breach-attribution taxonomy
(docs/engine/semantics.md Section 9, final locked correction).

The *only* safety predicate: a candidate is safe iff
``plan_low(d) >= reserve`` for every day ``d`` from its first payment
date through ``effective_end``. A baseline breach is never itself a
rejection reason — it is purely explanatory, via the four-way
``causes`` / ``worsens`` / ``unrelated`` / ``neither`` classification.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from finguard_core.contracts import BreachAttribution, BreachDay, LedgerDay
from finguard_core.forecast import BaselineForecast


def build_plan_series(
    baseline: BaselineForecast, extra_debits: dict[date, Decimal]
) -> dict[date, LedgerDay]:
    """Re-walk the ledger with ``extra_debits`` (a candidate's payment
    schedule, already converted to the home currency) added on top of
    the baseline's own debit totals.
    """

    plan_by_date: dict[date, LedgerDay] = {}
    running_close = baseline.opening_balance
    for base_day in baseline.series:
        day = base_day.day
        debit = baseline.debit_totals.get(day, Decimal(0)) + extra_debits.get(day, Decimal(0))
        low = running_close - debit
        close = low + baseline.credit_totals.get(day, Decimal(0))
        plan_by_date[day] = LedgerDay(day=day, low=low, close=close)
        running_close = close
    return plan_by_date


def classify_breach_day(
    day: date, baseline_low: Decimal, plan_low: Decimal, reserve: Decimal
) -> BreachAttribution:
    """Per-day classification against the locked G.9 taxonomy. Only
    called for a day where ``plan_low < reserve``; callers must not call
    this for a safe day, since ``NEITHER`` is reserved for safe days and
    this function never returns it.
    """

    if plan_low >= reserve:
        raise AssertionError("classify_breach_day called for a safe day")
    if baseline_low >= reserve:
        return BreachAttribution.CAUSES
    if plan_low < baseline_low:
        return BreachAttribution.WORSENS
    return BreachAttribution.UNRELATED


def evaluate_candidate_safety(
    baseline: BaselineForecast,
    plan_by_date: dict[date, LedgerDay],
    first_payment_date: date,
    effective_end: date,
    reserve: Decimal,
) -> tuple[bool, tuple[BreachDay, ...]]:
    breach_days: list[BreachDay] = []
    day = first_payment_date
    while day <= effective_end:
        plan_day = plan_by_date.get(day)
        baseline_day = baseline.series_by_date.get(day)
        if plan_day is None or baseline_day is None:
            day = day + timedelta(days=1)
            continue
        if plan_day.low < reserve:
            attribution = classify_breach_day(day, baseline_day.low, plan_day.low, reserve)
            breach_days.append(
                BreachDay(
                    day=day,
                    attribution=attribution,
                    baseline_low=baseline_day.low,
                    plan_low=plan_day.low,
                    reserve=reserve,
                )
            )
        day = day + timedelta(days=1)

    safe = len(breach_days) == 0
    return safe, tuple(breach_days)


def baseline_has_breach(baseline: BaselineForecast, reserve: Decimal) -> bool:
    return any(day.low < reserve for day in baseline.series)
