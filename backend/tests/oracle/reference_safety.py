"""An independent, from-spec reference implementation of the G.9 safety
predicate, used only to check production code's behavior against the
specification — never imported by, or importing, any production module
(enforced by ``test_oracle_independence.py``).

This file is deliberately written without looking at
``finguard_core.safety``'s source; it re-derives the predicate directly
from docs/engine/semantics.md Section 9:

    "a candidate is safe if and only if plan_low(d) >= reserve for every
    day d from its first payment date through effective_end."

and the breach-attribution rules from the same section.
"""

from __future__ import annotations

from datetime import date, timedelta


def reference_is_safe(
    plan_low_by_day: dict[date, float],
    reserve: float,
    first_payment_date: date,
    effective_end: date,
) -> bool:
    day = first_payment_date
    while day <= effective_end:
        if plan_low_by_day.get(day, reserve) < reserve:
            return False
        day += timedelta(days=1)
    return True


def reference_breach_attribution(baseline_low: float, plan_low: float, reserve: float) -> str:
    assert plan_low < reserve, "only defined for an unsafe day"
    if baseline_low >= reserve:
        return "causes"
    if plan_low < baseline_low:
        return "worsens"
    return "unrelated"


def reference_plan_low(opening_balance: float, debits_by_day: dict[date, float], day: date, start: date) -> float:
    """A direct, independent re-walk of the ledger from ``start`` to
    ``day``: running balance minus that day's debits. No suffix-min
    trick, no shared code with the production ``forecast``/``safety``
    modules — just the definition, walked naively.
    """

    balance = opening_balance
    current = start
    low = balance
    while current <= day:
        debit_today = debits_by_day.get(current, 0.0)
        low = balance - debit_today
        balance = low  # credits are not modeled in this minimal oracle;
        # production code's credit handling is covered by the scenario
        # and unit suites, which do model credits explicitly.
        current += timedelta(days=1)
    return low
